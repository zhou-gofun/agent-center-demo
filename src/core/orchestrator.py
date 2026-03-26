"""
Agent 编排器

实现多 Agent 协作流程，支持流式输出和用户确认
"""
import json
import time
from typing import Dict, List, Any, Generator, Optional
from src.core.llm_client import QwenClient
from src.core.agent_manager import AgentManager
from src.core.skill_manager import SkillManager
from src.vector_db.chroma_store import get_vector_store
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OrchestratorEvent:
    """编排事件"""

    def __init__(self, event_type: str, content: str = "", metadata: dict = None):
        self.event_type = event_type  # start, thinking, search, agent_call, response, confirm, end
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = time.time()

    def to_dict(self) -> Dict:
        return {
            "type": self.event_type,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


class AgentOrchestrator:
    """
    Agent 编排器

    实现流程: 用户问题 → 搜索知识库 → 思考 → 调用 Agent → (确认) → 输出
    """

    def __init__(self):
        self.llm = QwenClient()
        self.agent_manager = AgentManager()
        self.skill_manager = SkillManager()
        self.vector_store = None

    def _get_vector_store(self):
        """获取向量存储（懒加载）"""
        if self.vector_store is None:
            self.vector_store = get_vector_store()
        return self.vector_store

    def stream_execute(
        self,
        query: str,
        context: Dict = None,
        require_confirmation: bool = True
    ) -> Generator[OrchestratorEvent, None, None]:
        """
        流式执行编排流程

        Args:
            query: 用户问题
            context: 上下文信息
            require_confirmation: 是否需要确认

        Yields:
            OrchestratorEvent 事件
        """
        context = context or {}

        # 1. 开始事件
        yield OrchestratorEvent("start", f"开始处理问题: {query}")

        # 2. 搜索知识库
        yield OrchestratorEvent("thinking", "正在搜索知识库...")
        search_results = self._search_knowledge(query)
        yield OrchestratorEvent("search", f"找到 {len(search_results)} 条相关知识", {
            "results": search_results[:3]  # 只返回前3条
        })

        # 3. 路由决策
        yield OrchestratorEvent("thinking", "正在分析问题并决定处理方式...")
        routing_decision = self._make_routing_decision(query, search_results, context)

        target_agent = routing_decision.get("target")
        reasoning = routing_decision.get("reasoning", "")

        yield OrchestratorEvent("thinking", f"分析结果: {reasoning}")

        # 4. 如果是 pipeline-agent，需要确认
        if target_agent == "pipeline-agent" and require_confirmation:
            yield OrchestratorEvent("confirm", "是否需要进行统计流程组配？", {
                "target_agent": target_agent,
                "reasoning": reasoning
            })
            # 等待外部确认（通过后续请求）
            yield OrchestratorEvent("waiting", "等待用户确认...")
            return

        # 5. 调用目标 Agent
        yield OrchestratorEvent("agent_call", f"正在调用 {target_agent}...", {
            "agent": target_agent
        })

        agent_result = self._call_agent(target_agent, query, context, search_results)

        # 6. 返回最终结果
        yield OrchestratorEvent("response", agent_result, {
            "agent_used": target_agent,
            "search_results_count": len(search_results)
        })

        yield OrchestratorEvent("end", "处理完成")

    def _search_knowledge(self, query: str, top_k: int = 5) -> List[Dict]:
        """搜索知识库"""
        try:
            db = self._get_vector_store()
            collections = db.list_collections()

            all_results = []
            for collection in collections:
                try:
                    results = db.search(collection, query, top_k=3)
                    all_results.extend(results)
                except:
                    pass

            # 按分数排序
            all_results.sort(key=lambda x: x.get('score', 0), reverse=True)
            return all_results[:top_k]

        except Exception as e:
            logger.warning(f"知识库搜索失败: {e}")
            return []

    def _make_routing_decision(self, query: str, search_results: List[Dict], context: Dict) -> Dict:
        """做出路由决策"""
        # 构建决策提示
        search_context = "\n".join([
            f"- {r.get('metadata', {}).get('toolname', 'N/A')}: {r.get('document', '')[:100]}"
            for r in search_results[:3]
        ])

        prompt = f"""你是路由决策者。根据用户问题和知识库搜索结果，决定如何处理。

用户问题: {query}

知识库搜索结果:
{search_context}

可用 Agents:
- pipeline-agent: 统计分析流程组配
- data-analyst-agent: 数据分析和代码生成
- general-purpose-agent: 通用问题解答

请做出决策并返回 JSON 格式:
{{
  "target": "agent_name",
  "reasoning": "决策理由",
  "action": "route_to_agent|direct_response"
}}

如果需要生成统计分析流程，选择 pipeline-agent。
如果需要代码或数据分析，选择 data-analyst-agent。
如果是简单问答，选择 general-purpose-agent。"""

        response = self.llm.chat([{"role": "user", "content": prompt}], temperature=0.3)

        # 解析 JSON
        try:
            # 提取 JSON
            import re
            json_match = re.search(r'\{[^{}]*"target"[^{}]*\}', response, re.DOTALL)
            if not json_match:
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)

            if json_match:
                json_str = json_match.group(1) if json_match.lastindex else json_match.group()
                return json.loads(json_str)
        except:
            pass

        # 默认路由
        return {
            "target": "general-purpose-agent",
            "reasoning": "使用默认路由",
            "action": "route_to_agent"
        }

    def _call_agent(self, agent_name: str, query: str, context: Dict, search_results: List[Dict]) -> str:
        """调用指定的 Agent"""
        from src.core.executor import get_executor
        executor = get_executor()

        # 构建输入，包含搜索结果
        agent_input = {
            "query": query,
            "knowledge_context": search_results
        }
        agent_input.update(context)

        result = executor.execute_agent(agent_name, agent_input)

        if result.success:
            return result.response
        else:
            return f"执行出错: {result.response}"


class StreamingOrchestrator:
    """支持流式输出的编排器"""

    def __init__(self):
        self.orchestrator = AgentOrchestrator()
        self._pending_confirmations = {}

    def execute_stream(self, session_id: str, query: str, context: Dict = None) -> List[Dict]:
        """
        执行流式编排

        Returns:
            事件列表
        """
        events = []
        for event in self.orchestrator.stream_execute(query, context):
            events.append(event.to_dict())

            # 如果需要确认，保存状态
            if event.event_type == "waiting":
                self._pending_confirmations[session_id] = {
                    "query": query,
                    "context": context,
                    "events": events
                }
                break

        return events

    def confirm_and_continue(self, session_id: str, confirmed: bool) -> List[Dict]:
        """
        确认后继续执行

        Args:
            session_id: 会话 ID
            confirmed: 是否确认

        Returns:
            事件列表
        """
        if session_id not in self._pending_confirmations:
            return [{"type": "error", "content": "会话不存在或已过期"}]

        state = self._pending_confirmations[session_id]

        if not confirmed:
            del self._pending_confirmations[session_id]
            return [{"type": "end", "content": "用户取消操作"}]

        # 继续执行 pipeline-agent
        events = []
        from src.core.executor import get_executor
        executor = get_executor()

        events.append({
            "type": "agent_call",
            "content": "正在调用 pipeline-agent...",
            "metadata": {"agent": "pipeline-agent"}
        })

        result = executor.execute_agent("pipeline-agent", {
            "query": state["query"],
            **state["context"]
        })

        events.append({
            "type": "response",
            "content": result.response if result.success else f"执行失败: {result.response}",
            "metadata": {"agent_used": "pipeline-agent"}
        })

        events.append({"type": "end", "content": "处理完成"})

        del self._pending_confirmations[session_id]
        return events


# 全局实例
_streaming_orchestrator = None


def get_streaming_orchestrator() -> StreamingOrchestrator:
    """获取流式编排器实例"""
    global _streaming_orchestrator
    if _streaming_orchestrator is None:
        _streaming_orchestrator = StreamingOrchestrator()
    return _streaming_orchestrator
