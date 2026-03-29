"""
Flask REST API 路由

提供 Agent 中心的 HTTP API 接口（带调试追踪）
"""
from flask import Blueprint, request, jsonify
from typing import Dict, Any
from core.executor import get_executor
from core.agent_manager import AgentManager
from core.skill_manager import SkillManager
from vector_db.chroma_store import get_vector_store
from vector_db.embeddings import get_embedding_function
from vector_db.data_loader import get_assembly_loader, get_literature_loader
from utils.logger import get_logger
from utils.debug import log_agent_execution, enable_debug_mode

logger = get_logger(__name__)



# 创建蓝图
api_bp = Blueprint('api', __name__, url_prefix='/v1')

# 初始化组件
executor = get_executor()
agent_manager = AgentManager()
skill_manager = SkillManager()
vector_store = None

# 调试模式开关
DEBUG_MODE = True  # 设置为 True 启用详细日志


def get_vector_db():
    """获取向量数据库实例（懒加载）"""
    global vector_store
    if vector_store is None:
        from vector_db.chroma_store import get_vector_store as _get_store
        from vector_db.embeddings import get_embedding_function
        vector_store = _get_store()
        # 初始化集合
        embedding_fn = get_embedding_function()
        # 创建默认集合
        for collection_name in ["assembly_tools", "literature"]:
            if collection_name not in vector_store.list_collections():
                vector_store.create_collection(collection_name, embedding_fn)
    return vector_store


# ==================== 统一聊天接口（唯一对外接口）====================

@api_bp.route('/chat', methods=['POST'])
def unified_chat():
    """
    统一聊天接口 - 项目唯一对外暴露的入口

    外部只需传入上下文和问题，系统自动处理

    Request:
    {
      "query": "用户问题",
      "context": {
        "data_summary": "数据摘要",
        "user_id": "用户ID",
        ...其他自定义上下文
      }
    }

    Response:
    {
      "success": true,
      "data": {
        "response": "处理结果",
        "agent_used": "实际调用的agent",
        "execution_time": 1.23,
        "debug": {...}  # 调试信息（如果启用）
      }
    }
    """
    import time
    import re
    import json

    # 调试信息收集
    debug_info = {
        "steps": [],
        "timing": {},
        "agents_called": []
    }

    try:
        query = request.json.get('query', '')
        context = request.json.get('context', {})

        if not query:
            return jsonify({
                "success": False,
                "error": "Missing 'query' field"
            }), 400

        request_start = time.time()

        # ========== 步骤 1: 请求接收与预处理 ==========
        if DEBUG_MODE:
            print(f"\n{'-'*70}")
            print(f"📥 REQUEST RECEIVED")
            print(f"{'-'*70}")
            print(f"Query: {query}")
            print(f"Context keys: {list(context.keys())}")

        debug_info["steps"].append({"step": "request_received", "time": 0})
        step1_time = time.time()

        # 处理对话历史
        conversation_history = context.pop('conversation_history', [])
        history_context = ""
        raw_history = ""
        if conversation_history:
            if DEBUG_MODE:
                print(f"📜 Conversation history: {len(conversation_history)} messages")

            # ===== 清理对话历史中的重复问候 =====
            cleaned_history = []
            greeting_count = 0
            for msg in conversation_history:
                content = msg.get('content', '').strip()
                content_lower = content.lower()

                # 跳过重复的问候
                if any(g in content_lower for g in ["哈喽", "你好", "hello", "嗨", "您好"]):
                    greeting_count += 1
                    if greeting_count > 1:  # 跳过第2个及以后的问候
                        continue

                cleaned_history.append(msg)

            if DEBUG_MODE and greeting_count > 1:
                print(f"🧹 Cleaned {greeting_count - 1} repetitive greetings")

            # 格式化对话历史供 agent 参考
            history_items = []
            raw_items = []
            for msg in cleaned_history[-8:]:  # 保留最近8条
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                history_items.append(f"{role}: {content[:300]}")  # 摘要
                raw_items.append(f"{role}: {content}")  # 完整内容
            history_context = "对话摘要：\n" + "\n".join(history_items) + "\n\n"
            raw_history = "完整对话历史：\n" + "\n".join(raw_items) + "\n\n"

        # ========== 步骤 2: 知识库搜索 ==========
        step2_start = time.time()
        search_results = []
        if context.get('enable_search', True):
            if DEBUG_MODE:
                print(f"🔍 Searching knowledge base...")

            try:
                db = get_vector_db()
                collections = db.list_collections()
                if DEBUG_MODE:
                    print(f"   Collections: {collections}")

                for collection in collections:
                    try:
                        results = db.search(collection, query, top_k=3)
                        search_results.extend(results)
                        if DEBUG_MODE and results:
                            print(f"   {collection}: {len(results)} results")
                    except Exception as e:
                        if DEBUG_MODE:
                            print(f"   {collection} search failed: {e}")
                search_results.sort(key=lambda x: x.get('score', 0), reverse=True)
                search_results = search_results[:5]

                if DEBUG_MODE:
                    print(f"✓ Total search results: {len(search_results)}")
            except Exception as e:
                if DEBUG_MODE:
                    print(f"✗ Search failed: {e}")

        debug_info["steps"].append({"step": "knowledge_search", "time": time.time() - step2_start})
        debug_info["search_results_count"] = len(search_results)

        # ========== 步骤 3: 路由决策 ==========
        step3_start = time.time()

        if DEBUG_MODE:
            print(f"\n🔀 ROUTING DECISION")
            print(f"{'─'*40}")

        routing_input = {
            "query": raw_history + query,  # 使用完整历史
            "conversation_history": conversation_history,  # 传递原始对话历史
            "knowledge_results": search_results[:2],
            **context
        }

        routing_result = executor.execute_agent('routing-agent', routing_input)

        if DEBUG_MODE:
            print(f"Routing response:")
            print(f"   {routing_result.response[:300]}...")

        agent_used = "routing-agent"
        response = routing_result.response

        debug_info["steps"].append({"step": "routing", "time": time.time() - step3_start})
        debug_info["agents_called"].append("routing-agent")

        # ========== 步骤 4: 解析路由并调用目标 agent ==========
        step4_start = time.time()
        target_agent = None

        try:
            # 尝试多种 JSON 提取模式
            json_match = (
                re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL) or
                re.search(r'\{[^{}]*"target"[^{}]*"action"[^{}]*\}', response, re.DOTALL) or
                re.search(r'\{[^{}]*"action"[^{}]*"target"[^{}]*\}', response, re.DOTALL)
            )

            if json_match:
                json_str = json_match.group(1) if json_match.lastindex else json_match.group()
                route_info = json.loads(json_str)
                target = route_info.get("target")
                action = route_info.get("action")

                if DEBUG_MODE:
                    print(f"\n🎯 Parsed routing decision:")
                    print(f"   Action: {action}")
                    print(f"   Target: {target}")
                    print(f"   Reasoning: {route_info.get('reasoning', 'N/A')}")

                if action == "route_to_agent" and target and target != "direct_response":
                    # 自动路由到目标 agent（包含完整对话历史）
                    target_agent = target

                    if DEBUG_MODE:
                        print(f"\n{'-'*70}")
                        print(f"🚀 CALLING TARGET AGENT: {target}")
                        print(f"{'-'*70}")

                    agent_input = {
                        "query": raw_history + query,  # 使用完整历史
                        "conversation_history": conversation_history,  # 传递原始历史
                        **context
                    }
                    if search_results:
                        agent_input["knowledge_context"] = search_results

                    target_result = executor.execute_agent(target, agent_input)
                    response = target_result.response
                    agent_used = target

                    if DEBUG_MODE:
                        print(f"\n✓ Target agent response received")
                        print(f"   Response length: {len(response)} chars")

                    debug_info["agents_called"].append(target)

        except Exception as e:
            if DEBUG_MODE:
                print(f"✗ Routing parse failed: {e}")
            logger.debug(f"Routing parse failed: {e}")

        debug_info["steps"].append({"step": "target_execution", "time": time.time() - step4_start})

        # ========== 步骤 5: 最终响应 ==========
        execution_time = time.time() - request_start

        if DEBUG_MODE:
            print(f"\n{'-'*70}")
            print(f"✅ REQUEST COMPLETE")
            print(f"{'-'*70}")
            print(f"Agent used: {agent_used}")
            print(f"Total time: {execution_time:.3f}s")
            print(f"Agents called: {' → '.join(debug_info['agents_called'])}")
            print(f"{'-'*70}\n")

        result_data = {
            "response": response,
            "agent_used": agent_used,
            "execution_time": round(execution_time, 2)
        }

        # 添加调试信息（如果启用）
        if DEBUG_MODE:
            result_data["debug"] = debug_info

        return jsonify({
            "success": True,
            "data": result_data
        })

    except Exception as e:
        logger.error(f"Error in unified_chat: {e}")
        if DEBUG_MODE:
            import traceback
            print(f"\n❌ ERROR: {e}")
            traceback.print_exc()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ==================== Agent 执行接口 ====================

@api_bp.route('/agent/<agent_name>/execute', methods=['POST'])
def execute_agent_route(agent_name: str):
    """直接执行指定的 agent（调试用）"""
    try:
        input_data = request.json.get('input', {})

        if DEBUG_MODE:
            print(f"\n{'-'*70}")
            print(f"🔧 DIRECT AGENT EXECUTION: {agent_name}")
            print(f"{'-'*70}")

        result = executor.execute_agent(agent_name, input_data)

        if DEBUG_MODE:
            print(f"✓ Execution complete")

        return jsonify({
            "success": result.success,
            "data": result.to_dict()
        })
    except Exception as e:
        logger.error(f"Error in execute_agent: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ==================== 注册表管理接口 ====================

@api_bp.route('/registry/agents', methods=['GET'])
def list_agents():
    """列出所有 agents"""
    try:
        agents = agent_manager.list_agents()
        if DEBUG_MODE:
            print(f"📋 Listing {len(agents)} agents")
        return jsonify({
            "success": True,
            "data": agents
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/registry/skills', methods=['GET'])
def list_skills():
    """列出所有 skills"""
    try:
        skills = skill_manager.list_skills()
        if DEBUG_MODE:
            print(f"📋 Listing {len(skills)} skills")
        return jsonify({
            "success": True,
            "data": skills
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== 知识库接口 ====================

@api_bp.route('/knowledge/search', methods=['POST'])
def knowledge_search():
    """知识库搜索"""
    try:
        query = request.json.get('query', '')
        collection = request.json.get('collection', 'assembly_tools')
        top_k = request.json.get('top_k', 10)

        if not query:
            return jsonify({"success": False, "error": "Missing 'query'"}), 400

        if DEBUG_MODE:
            print(f"\n🔍 KNOWLEDGE SEARCH")
            print(f"   Query: {query}")
            print(f"   Collection: {collection}")
            print(f"   Top-K: {top_k}")

        db = get_vector_db()
        collection_map = {"assembly": "assembly_tools", "literature": "literature"}
        collection_name = collection_map.get(collection, collection)

        results = db.search(collection_name, query, top_k=top_k)

        if DEBUG_MODE:
            print(f"   Results: {len(results)} items")
            for r in results[:3]:
                score = r.get("score", 0)
                name = r.get("metadata", {}).get("toolname", r.get("title", "N/A"))
                print(f"      - {name} ({score:.2f})")

        return jsonify({
            "success": True,
            "data": results
        })
    except Exception as e:
        if DEBUG_MODE:
            print(f"✗ Search failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== 调试控制接口 ====================

@api_bp.route('/debug/toggle', methods=['POST'])
def toggle_debug():
    """切换调试模式"""
    global DEBUG_MODE
    DEBUG_MODE = not DEBUG_MODE
    return jsonify({
        "success": True,
        "data": {"debug_mode": DEBUG_MODE}
    })


@api_bp.route('/debug/status', methods=['GET'])
def debug_status():
    """获取调试状态"""
    return jsonify({
        "success": True,
        "data": {
            "debug_mode": DEBUG_MODE,
            "log_level": "DEBUG" if DEBUG_MODE else "INFO"
        }
    })


# ==================== 健康检查 ====================

@api_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        "status": "healthy",
        "service": "agent-center",
        "debug_mode": DEBUG_MODE
    })


@api_bp.route('/info', methods=['GET'])
def service_info():
    """服务信息"""
    try:
        agents = agent_manager.list_agents()
        skills = skill_manager.list_skills()

        return jsonify({
            "success": True,
            "data": {
                "version": "1.0.0",
                "debug_mode": DEBUG_MODE,
                "agents_count": len(agents),
                "skills_count": len(skills),
                "agents": [a["name"] for a in agents],
                "skills": [s["name"] for s in skills]
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
