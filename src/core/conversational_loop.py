"""
对话循环管理器

支持多轮对话、追问、迭代式任务处理
"""
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from src.core.execution_context import ExecutionContext
from src.core.execution_orchestrator import ExecutionOrchestrator
from src.core.task_parser import ActionType
from src.utils.logger import get_logger

logger = get_logger(__name__)


class LoopState(Enum):
    """循环状态"""
    IDLE = "idle"
    PROCESSING = "processing"
    WAITING_USER = "waiting_user"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ConversationTurn:
    """单轮对话"""
    turn_id: int
    user_input: str
    agent_response: str
    tasks_executed: List[Dict] = field(default_factory=list)
    needs_followup: bool = False
    followup_question: str = ""


@dataclass
class LoopContext:
    """循环上下文"""
    session_id: str
    max_iterations: int = 10
    current_iteration: int = 0
    state: LoopState = LoopState.IDLE
    turns: List[ConversationTurn] = field(default_factory=list)
    execution_context: Optional[ExecutionContext] = None
    pending_question: str = ""


class ConversationalLoop:
    """
    对话循环管理器

    功能：
    1. 管理多轮对话
    2. 处理追问和用户反馈
    3. 支持迭代式任务处理
    4. 状态跟踪和恢复
    """

    def __init__(self, orchestrator: Optional[ExecutionOrchestrator] = None):
        """
        初始化

        Args:
            orchestrator: 执行编排器
        """
        self.orchestrator = orchestrator
        self.sessions: Dict[str, LoopContext] = {}

    def create_session(
        self,
        session_id: str,
        agent_name: str = "general-purpose-agent",
        max_iterations: int = 10
    ) -> LoopContext:
        """
        创建新的会话

        Args:
            session_id: 会话 ID
            agent_name: 初始 agent
            max_iterations: 最大迭代次数

        Returns:
            会话上下文
        """
        context = LoopContext(
            session_id=session_id,
            max_iterations=max_iterations,
            state=LoopState.PROCESSING,
            execution_context=ExecutionContext()
        )

        self.sessions[session_id] = context
        logger.info(f"Created session {session_id} with agent {agent_name}")
        return context

    def process_turn(
        self,
        session_id: str,
        user_input: str,
        agent_name: str = "general-purpose-agent"
    ) -> Dict:
        """
        处理一轮对话

        Args:
            session_id: 会话 ID
            user_input: 用户输入
            agent_name: 要调用的 agent

        Returns:
            处理结果
        """
        context = self.sessions.get(session_id)
        if not context:
            context = self.create_session(session_id, agent_name)

        if context.state == LoopState.COMPLETED:
            return {
                "status": "completed",
                "message": "Session is already completed"
            }

        if context.current_iteration >= context.max_iterations:
            context.state = LoopState.COMPLETED
            return {
                "status": "completed",
                "message": f"Max iterations ({context.max_iterations}) reached"
            }

        try:
            context.state = LoopState.PROCESSING
            context.current_iteration += 1

            # 准备输入
            input_data = {"query": user_input}

            # 如果有待处理的追问，添加上下文
            if context.pending_question:
                input_data["previous_question"] = context.pending_question
                context.pending_question = ""

            # 执行 agent
            if not self.orchestrator:
                from src.core.execution_orchestrator import get_orchestrator
                self.orchestrator = get_orchestrator()

            result = self.orchestrator.execute_agent(
                agent_name,
                input_data,
                context.execution_context
            )

            # 检查是否有追问
            response = result.get("response", "")
            tasks = result.get("tasks_executed", [])

            turn = ConversationTurn(
                turn_id=context.current_iteration,
                user_input=user_input,
                agent_response=response,
                tasks_executed=[]
            )

            # 检查任务结果中是否有追问
            task_results = result.get("task_results", [])
            for tr in task_results:
                turn.tasks_executed.append(tr)
                if tr.get("type") == "ask_user" and tr.get("needs_input"):
                    turn.needs_followup = True
                    turn.followup_question = tr.get("question", "")
                    context.pending_question = tr.get("question", "")
                    context.state = LoopState.WAITING_USER

            context.turns.append(turn)

            # 如果没有追问，标记为完成本轮
            if not turn.needs_followup:
                context.state = LoopState.IDLE

            return {
                "status": "success",
                "response": response,
                "turn_id": context.current_iteration,
                "needs_followup": turn.needs_followup,
                "followup_question": turn.followup_question,
                "iteration": context.current_iteration,
                "max_iterations": context.max_iterations
            }

        except Exception as e:
            logger.error(f"Error processing turn: {e}")
            context.state = LoopState.ERROR
            return {
                "status": "error",
                "error": str(e)
            }

    def answer_followup(
        self,
        session_id: str,
        user_answer: str,
        agent_name: str = "general-purpose-agent"
    ) -> Dict:
        """
        回答追问

        Args:
            session_id: 会话 ID
            user_answer: 用户回答
            agent_name: 要调用的 agent

        Returns:
            处理结果
        """
        context = self.sessions.get(session_id)
        if not context:
            return {
                "status": "error",
                "error": "Session not found"
            }

        # 构建包含问题的输入
        full_input = f"Previous question: {context.pending_question}\nUser answer: {user_answer}"

        return self.process_turn(session_id, full_input, agent_name)

    def get_session(self, session_id: str) -> Optional[LoopContext]:
        """获取会话上下文"""
        return self.sessions.get(session_id)

    def end_session(self, session_id: str) -> bool:
        """
        结束会话

        Args:
            session_id: 会话 ID

        Returns:
            是否成功
        """
        if session_id in self.sessions:
            self.sessions[session_id].state = LoopState.COMPLETED
            logger.info(f"Session {session_id} ended")
            return True
        return False

    def get_conversation_summary(self, session_id: str) -> Optional[Dict]:
        """
        获取对话摘要

        Args:
            session_id: 会话 ID

        Returns:
            对话摘要
        """
        context = self.sessions.get(session_id)
        if not context:
            return None

        return {
            "session_id": session_id,
            "state": context.state.value,
            "iterations": context.current_iteration,
            "turns": [
                {
                    "turn_id": t.turn_id,
                    "user_input_length": len(t.user_input),
                    "response_length": len(t.agent_response),
                    "tasks_executed": len(t.tasks_executed),
                    "had_followup": t.needs_followup
                }
                for t in context.turns
            ]
        }


# 全局实例
_loop: Optional[ConversationalLoop] = None


def get_conversational_loop() -> ConversationalLoop:
    """获取对话循环实例"""
    global _loop
    if _loop is None:
        from src.core.execution_orchestrator import get_orchestrator
        _loop = ConversationalLoop(orchestrator=get_orchestrator())
    return _loop
