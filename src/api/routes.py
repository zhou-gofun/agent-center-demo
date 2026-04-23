"""
Flask REST API routes for Agent Center.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List

from flask import Blueprint, jsonify, request

from api.response_utils import error_response, success_response
from core.agent_manager import AgentManager
from core.registry_scanner import get_scanner
from core.simple_agent_executor import get_simple_executor
from core.skill_manager import SkillManager
from utils.logger import get_logger
from vector_db.chroma_store import get_vector_store
from vector_db.embeddings import get_embedding_function

logger = get_logger(__name__)

api_bp = Blueprint("api", __name__, url_prefix="/v1")

simple_executor = get_simple_executor()
agent_manager = AgentManager()
skill_manager = SkillManager()
registry_scanner = get_scanner()
vector_store = None

DEBUG_MODE = True


def _get_json_payload() -> Dict[str, Any]:
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}


def get_vector_db():
    """Return a lazily initialized vector DB client."""

    global vector_store
    if vector_store is None:
        vector_store = get_vector_store()
        embedding_fn = get_embedding_function()
        for collection_name in ["assembly_tools", "literature"]:
            if collection_name not in vector_store.list_collections():
                vector_store.create_collection(collection_name, embedding_fn)
    return vector_store


def _build_debug_info() -> Dict[str, Any]:
    return {"steps": [], "timing": {}, "agents_called": []}


def _extract_route_json(response: str) -> Dict[str, Any]:
    json_match = (
        re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
        or re.search(r"\{[^{}]*\"target\"[^{}]*\"action\"[^{}]*\}", response, re.DOTALL)
        or re.search(r"\{[^{}]*\"action\"[^{}]*\"target\"[^{}]*\}", response, re.DOTALL)
    )
    if not json_match:
        return {}

    json_str = json_match.group(1) if json_match.lastindex else json_match.group()
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return {}


def _search_knowledge(query: str, enable_search: bool = True) -> List[Dict[str, Any]]:
    if not enable_search:
        return []

    try:
        db = get_vector_db()
        search_results: List[Dict[str, Any]] = []
        for collection in db.list_collections():
            try:
                search_results.extend(db.search(collection, query, top_k=3))
            except Exception as exc:
                logger.warning("Knowledge search failed for %s: %s", collection, exc)

        search_results.sort(key=lambda item: item.get("score", 0), reverse=True)
        return search_results[:5]
    except Exception as exc:
        logger.warning("Knowledge base search unavailable: %s", exc)
        return []


@api_bp.route("/chat", methods=["POST"])
def unified_chat():
    """Unified chat endpoint with routing and optional knowledge search."""

    debug_info = _build_debug_info()

    try:
        payload = _get_json_payload()
        query = payload.get("query", "")
        context = dict(payload.get("context", {}) or {})

        if not query:
            body, status = error_response("Missing 'query' field", 400, code="missing_query")
            return jsonify(body), status

        request_start = time.time()
        conversation_history = context.pop("conversation_history", [])
        raw_history = ""
        if conversation_history:
            raw_items = []
            for message in conversation_history[-8:]:
                role = message.get("role", "user")
                content = message.get("content", "")
                raw_items.append(f"{role}: {content}")
            raw_history = "Conversation history:\n" + "\n".join(raw_items) + "\n\n"

        step_start = time.time()
        search_results = _search_knowledge(query, enable_search=context.get("enable_search", True))
        debug_info["steps"].append({"step": "knowledge_search", "time": time.time() - step_start})
        debug_info["search_results_count"] = len(search_results)

        routing_input = {
            "query": raw_history + query,
            "conversation_history": conversation_history,
            "knowledge_results": search_results[:2],
            **context,
        }

        step_start = time.time()
        routing_result = simple_executor.execute("routing-agent", routing_input)
        debug_info["steps"].append({"step": "routing", "time": time.time() - step_start})
        debug_info["agents_called"].append("routing-agent")

        response = routing_result.get("response", "")
        agent_used = "routing-agent"
        route_info = _extract_route_json(response)

        step_start = time.time()
        target = route_info.get("target")
        action = route_info.get("action")
        if action == "route_to_agent" and target and target != "direct_response":
            agent_input = {
                "query": raw_history + query,
                "conversation_history": conversation_history,
                **context,
            }
            if search_results:
                agent_input["knowledge_context"] = search_results

            target_result = simple_executor.execute(target, agent_input)
            response = target_result.get("response", "")
            agent_used = target
            debug_info["agents_called"].append(target)

        debug_info["steps"].append({"step": "target_execution", "time": time.time() - step_start})

        result = {
            "response": response,
            "agent_used": agent_used,
            "execution_time": round(time.time() - request_start, 2),
        }
        if DEBUG_MODE:
            result["debug"] = debug_info

        body, status = success_response(result)
        return jsonify(body), status

    except Exception as exc:
        logger.error("Error in unified_chat: %s", exc)
        body, status = error_response(str(exc), 500, code="chat_execution_failed")
        return jsonify(body), status


@api_bp.route("/agent/<agent_name>/execute", methods=["POST"])
def execute_agent_route(agent_name: str):
    """Direct agent execution endpoint."""

    try:
        payload = _get_json_payload()
        input_data = payload.get("input", {})
        result = simple_executor.execute(agent_name, input_data)

        if result.get("success", False):
            body, status = success_response(result)
            return jsonify(body), status

        error_text = result.get("error", "Agent execution failed")
        body, status = error_response(
            error_text,
            404 if "not found" in error_text.lower() else 400,
            code="agent_execution_failed",
            details=result,
        )
        return jsonify(body), status
    except Exception as exc:
        logger.error("Error in execute_agent_route: %s", exc)
        body, status = error_response(str(exc), 500, code="agent_route_failed")
        return jsonify(body), status


@api_bp.route("/registry/agents", methods=["GET"])
def list_agents():
    try:
        body, status = success_response(agent_manager.list_agents())
        return jsonify(body), status
    except Exception as exc:
        body, status = error_response(str(exc), 500, code="list_agents_failed")
        return jsonify(body), status


@api_bp.route("/registry/skills", methods=["GET"])
def list_skills():
    try:
        body, status = success_response(skill_manager.list_skills())
        return jsonify(body), status
    except Exception as exc:
        body, status = error_response(str(exc), 500, code="list_skills_failed")
        return jsonify(body), status


@api_bp.route("/registry/scan", methods=["GET"])
def scan_registry():
    """Scan registry and return validation report."""

    try:
        report = registry_scanner.scan()
        result = {
            "healthy": not report.get("errors"),
            "agents_count": len(report.get("agents", {})),
            "skills_count": len(report.get("skills", {})),
            "agents": sorted(report.get("agents", {}).keys()),
            "skills": sorted(report.get("skills", {}).keys()),
            "errors": report.get("errors", []),
        }
        body, status = success_response(result)
        return jsonify(body), status
    except Exception as exc:
        body, status = error_response(str(exc), 500, code="registry_scan_failed")
        return jsonify(body), status


@api_bp.route("/knowledge/search", methods=["POST"])
def knowledge_search():
    try:
        payload = _get_json_payload()
        query = payload.get("query", "")
        collection = payload.get("collection", "assembly_tools")
        top_k = payload.get("top_k", 10)

        if not query:
            body, status = error_response("Missing 'query'", 400, code="missing_query")
            return jsonify(body), status

        db = get_vector_db()
        collection_map = {"assembly": "assembly_tools", "literature": "literature"}
        collection_name = collection_map.get(collection, collection)
        results = db.search(collection_name, query, top_k=top_k)

        body, status = success_response(results)
        return jsonify(body), status
    except Exception as exc:
        body, status = error_response(str(exc), 500, code="knowledge_search_failed")
        return jsonify(body), status


@api_bp.route("/debug/toggle", methods=["POST"])
def toggle_debug():
    global DEBUG_MODE
    DEBUG_MODE = not DEBUG_MODE
    body, status = success_response({"debug_mode": DEBUG_MODE})
    return jsonify(body), status


@api_bp.route("/debug/status", methods=["GET"])
def debug_status():
    body, status = success_response(
        {"debug_mode": DEBUG_MODE, "log_level": "DEBUG" if DEBUG_MODE else "INFO"}
    )
    return jsonify(body), status


@api_bp.route("/health", methods=["GET"])
def health_check():
    scan_report = registry_scanner.get_last_scan_report()
    errors = scan_report.get("errors", [])
    body, status = success_response(
        {
            "status": "healthy" if not errors else "degraded",
            "service": "agent-center",
            "debug_mode": DEBUG_MODE,
            "registry": {
                "agents_count": len(scan_report.get("agents", {})),
                "skills_count": len(scan_report.get("skills", {})),
                "errors_count": len(errors),
            },
        }
    )
    return jsonify(body), status


@api_bp.route("/info", methods=["GET"])
def service_info():
    try:
        agents = agent_manager.list_agents()
        skills = skill_manager.list_skills()
        scan_report = registry_scanner.get_last_scan_report()
        body, status = success_response(
            {
                "version": "1.0.0",
                "debug_mode": DEBUG_MODE,
                "agents_count": len(agents),
                "skills_count": len(skills),
                "agents": [item["name"] for item in agents],
                "skills": [item["name"] for item in skills],
                "registry_errors": scan_report.get("errors", []),
            }
        )
        return jsonify(body), status
    except Exception as exc:
        body, status = error_response(str(exc), 500, code="service_info_failed")
        return jsonify(body), status
