"""
执行编排器

协调 Agent、Skill、Subagent 的执行，支持复杂任务流程
"""
import json
from typing import Dict, List, Any, Optional, Generator
from pathlib import Path

from src.core.execution_context import ExecutionContext
from src.core.task_parser import TaskParser, Task, ActionType
from src.core.python_script_executor import PythonScriptExecutor
from src.core.agent_manager import AgentManager
from src.core.skill_manager import SkillManager
from src.core.llm_client import QwenClient
from src.config import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ExecutionOrchestrator:
    """
    执行编排器

    核心功能：
    1. 上下文隔离管理
    2. Skill/Subagent 调度
    3. 任务链执行
    4. 结果聚合
    """

    def __init__(self):
        self.llm = QwenClient()
        self.agent_manager = AgentManager()
        self.skill_manager = SkillManager()
        self.script_executor = PythonScriptExecutor()
        self.task_parser = TaskParser()
        self.cfg = get_config()

    def execute_agent(
        self,
        agent_name: str,
        input_data: Dict,
        context: Optional[ExecutionContext] = None
    ) -> Dict:
        """
        执行 agent

        Args:
            agent_name: agent 名称
            input_data: 输入数据
            context: 执行上下文

        Returns:
            执行结果
        """
        # 创建或使用现有上下文
        if context is None:
            context = ExecutionContext()

        logger.info(f"Executing agent: {agent_name} in context {context.context_id}")

        # 获取 agent 配置
        agent_config = self.agent_manager.get_agent(agent_name)
        if not agent_config:
            return {
                "success": False,
                "error": f"Agent '{agent_name}' not found",
                "agent": agent_name
            }

        try:
            # 构建系统提示
            system_prompt = agent_config["prompt"]

            # 添加预加载的 skills 信息
            preloaded_skills = agent_config["frontmatter"].get("skills", [])
            if preloaded_skills:
                skill_list = "\n".join([f"- {s}" for s in preloaded_skills])
                system_prompt = f"""## Available Skills
You can request these skills when needed by using function call format:

{skill_list}

To use a skill, format your response as:
```json
{{
  "skill": "{preloaded_skills[0] if preloaded_skills else "skill_name"}",
  "action": "execute",
  "input": {{}},
  "reasoning": "Why this skill is needed"
}}
```

{system_prompt}"""

            # 构建消息（包含上下文历史）
            messages = [{"role": "system", "content": system_prompt}]

            # 添加上下文历史
            if context.conversation_history:
                messages.extend(context.conversation_history)

            # 添加当前输入
            user_message = self._format_input(input_data)
            messages.append({"role": "user", "content": user_message})

            # 调用 LLM
            response = self.llm.chat(messages, temperature=0.3)

            # 保存到上下文
            context.add_message("user", user_message)
            context.add_message("assistant", response)

            # 解析任务
            tasks = self.task_parser.parse(response)

            # 执行任务链
            results = self._execute_task_chain(tasks, input_data, context, agent_name)

            # 如果有任务执行，重新生成最终响应
            if results:
                final_response = self._generate_final_response(
                    response, results, messages, context
                )
                context.add_message("assistant", final_response)
                response = final_response

            return {
                "success": True,
                "agent": agent_name,
                "response": response,
                "context": context.to_dict(),
                "tasks_executed": len(results)
            }

        except Exception as e:
            logger.error(f"Error executing agent {agent_name}: {e}")
            return {
                "success": False,
                "agent": agent_name,
                "error": str(e)
            }

    def _execute_task_chain(
        self,
        tasks: List[Task],
        input_data: Dict,
        context: ExecutionContext,
        current_agent: str
    ) -> List[Dict]:
        """
        执行任务链

        Args:
            tasks: 任务列表
            input_data: 原始输入
            context: 执行上下文
            current_agent: 当前 agent

        Returns:
            执行结果列表
        """
        results = []

        for task in tasks:
            try:
                if task.action == ActionType.USE_SKILL:
                    result = self._execute_skill(task.data, input_data, context)
                    results.append({
                        "type": "skill",
                        "name": task.data.get("skill"),
                        "result": result
                    })

                elif task.action == ActionType.DELEGATE_TO_AGENT:
                    result = self._delegate_to_agent(task.data, input_data, context)
                    results.append({
                        "type": "agent",
                        "name": task.data.get("agent"),
                        "result": result
                    })

                elif task.action == ActionType.ASK_USER:
                    # 用户追问，暂停执行
                    results.append({
                        "type": "ask_user",
                        "question": task.data.get("question"),
                        "reasoning": task.data.get("reasoning", ""),
                        "needs_input": True
                    })
                    # 追问后不再执行后续任务
                    break

            except Exception as e:
                logger.error(f"Error executing task {task.action}: {e}")
                results.append({
                    "type": "error",
                    "action": task.action.value,
                    "error": str(e)
                })

        return results

    def _execute_skill(
        self,
        task_data: Dict,
        input_data: Dict,
        context: ExecutionContext
    ) -> Dict:
        """
        执行 skill

        Args:
            task_data: 任务数据（包含 skill 名称和输入）
            input_data: 原始输入
            context: 执行上下文

        Returns:
            执行结果
        """
        skill_name = task_data.get("skill")
        skill_input = task_data.get("input", {})

        # 合并输入数据
        merged_input = {**input_data, **skill_input}

        # 获取 skill 配置
        skill_config = self.skill_manager.get_skill(skill_name)
        if not skill_config:
            return {"error": f"Skill '{skill_name}' not found"}

        # 检查是否有 Python 实现
        skill_dir = Path(self.cfg.registry.skills_dir) / skill_name
        script_path = skill_dir / "__init__.py"

        if script_path.exists():
            # 执行 Python 脚本
            return self.script_executor.execute_skill_script(
                skill_name, script_path, merged_input
            )
        else:
            # 使用 LLM 执行
            return self._execute_skill_with_llm(
                skill_name, skill_config, merged_input, context
            )

    def _execute_skill_with_llm(
        self,
        skill_name: str,
        skill_config: Dict,
        input_data: Dict,
        context: ExecutionContext
    ) -> Dict:
        """使用 LLM 执行 skill"""
        system_prompt = skill_config["instructions"]

        allowed_tools = skill_config["frontmatter"].get("allowed-tools", [])
        if allowed_tools:
            tool_context = f"Available tools: {', '.join(allowed_tools)}"
            system_prompt = f"{tool_context}\n\n{system_prompt}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": self._format_input(input_data)}
        ]

        response = self.llm.chat(messages, temperature=0.3)

        return {"response": response}

    def _delegate_to_agent(
        self,
        task_data: Dict,
        input_data: Dict,
        parent_context: ExecutionContext
    ) -> Dict:
        """
        委派给 subagent

        Args:
            task_data: 任务数据（包含 agent 名称、上下文类型、输入）
            input_data: 原始输入
            parent_context: 父上下文

        Returns:
            执行结果
        """
        agent_name = task_data.get("agent")
        context_type = task_data.get("context", "inherit")
        agent_input = task_data.get("input", {})

        # 合并输入数据
        merged_input = {**input_data, **agent_input}

        # 创建子上下文
        if context_type == "fork":
            child_context = parent_context.create_fork()
        else:
            child_context = parent_context.create_inherit()

        # 执行 agent
        result = self.execute_agent(agent_name, merged_input, child_context)

        return {
            "agent": agent_name,
            "context_type": context_type,
            "response": result.get("response"),
            "context": result.get("context")
        }

    def _generate_final_response(
        self,
        original_response: str,
        task_results: List[Dict],
        messages: List[Dict],
        context: ExecutionContext
    ) -> str:
        """
        基于任务执行结果生成最终响应

        Args:
            original_response: 原始 LLM 响应
            task_results: 任务执行结果
            messages: 消息历史
            context: 执行上下文

        Returns:
            最终响应
        """
        # 构建结果上下文
        results_text = []
        for result in task_results:
            if result["type"] == "skill":
                skill_result = result["result"]
                if "error" not in skill_result:
                    results_text.append(
                        f"## Skill Result: {result['name']}\n"
                        f"```json\n{json.dumps(skill_result, ensure_ascii=False, indent=2)}\n```"
                    )
            elif result["type"] == "agent":
                agent_result = result["result"]
                results_text.append(
                    f"## Agent Result: {result['name']}\n"
                    f"{agent_result.get('response', '')[:500]}"
                )
            elif result["type"] == "ask_user":
                # 有追问，直接返回追问内容
                question = result["question"]
                reasoning = result.get("reasoning", "")
                return f"{reasoning}\n\n{question}" if reasoning else question

        if not results_text:
            return original_response

        # 让 LLM 基于结果生成响应
        prompt_messages = list(messages)
        prompt_messages.append({
            "role": "user",
            "content": "Based on the skill/agent execution results above, please provide your response to the user."
        })

        try:
            final_response = self.llm.chat(prompt_messages, temperature=0.3)
            return final_response
        except Exception as e:
            logger.error(f"Error generating final response: {e}")
            return original_response

    def _format_input(self, input_data: Dict) -> str:
        """格式化输入数据"""
        if "query" in input_data:
            return input_data["query"]
        if "prompt" in input_data:
            return input_data["prompt"]
        if "question" in input_data:
            return input_data["question"]
        return json.dumps(input_data, ensure_ascii=False, indent=2)


# 全局实例
_orchestrator = None


def get_orchestrator() -> ExecutionOrchestrator:
    """获取执行编排器实例"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ExecutionOrchestrator()
    return _orchestrator
