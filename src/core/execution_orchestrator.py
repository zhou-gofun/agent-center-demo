"""
执行编排器

协调 Agent、Skill、Subagent 的执行，支持复杂任务流程
"""
import json
from typing import Dict, List, Any, Optional, Generator
from pathlib import Path

from core.execution_context import ExecutionContext
from core.task_parser import TaskParser, Task, ActionType
from core.python_script_executor import PythonScriptExecutor
from core.universal_executor import get_universal_executor
from core.registry_scanner import get_scanner
from core.agent_manager import AgentManager
from core.skill_manager import SkillManager
from core.llm_client import QwenClient
from config import get_config
from utils.logger import get_logger

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
        self.universal_executor = get_universal_executor()
        self.registry_scanner = get_scanner()
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

            # 添加预加载的 skills 信息（支持自动发现）
            preloaded_skills = agent_config["frontmatter"].get("skills", [])

            # 如果 agent 没有配置 skills 列表，自动获取所有可用 skills
            if not preloaded_skills:
                preloaded_skills = self.registry_scanner.list_skills()

            if preloaded_skills:
                # 构建 skills 描述（包含 name 和 description）
                skill_descriptions = []
                for skill_name in preloaded_skills:
                    skill_spec = self.registry_scanner.get_skill_spec(skill_name)
                    if skill_spec:
                        desc = skill_spec["frontmatter"].get("description", "")
                        skill_descriptions.append(f"- **{skill_name}**: {desc}")

                skills_section = "\n".join(skill_descriptions)

                system_prompt = f"""## Available Skills
You have access to the following skills that you can use when needed:

{skills_section}

**How to use a skill:**
When you need to use a skill, format your response as:
```json
{{
  "skill": "skill_name",
  "action": "execute",
  "input": {{...}},
  "reasoning": "Why this skill is needed"
}}
```

The system will execute the skill and provide you with results.

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
                "tasks_executed": len(results),
                "task_results": results
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

        # 获取 skill spec（从扫描器）
        skill_spec = self.registry_scanner.get_skill_spec(skill_name)
        if not skill_spec:
            return {"error": f"Skill '{skill_name}' not found in registry"}

        # 检查执行配置
        execution_config = skill_spec.get("execution", {})
        exec_type = execution_config.get("type", "llm")

        if exec_type == "script":
            # 使用通用脚本执行器（只传递 skill 特定的 input）
            skill_dir = Path(self.cfg.registry.skills_dir) / skill_name
            return self.universal_executor.execute_skill(
                skill_name=skill_name,
                skill_dir=skill_dir,
                execution_config=execution_config,
                input_data=skill_input
            )
        else:
            # 使用 LLM 执行
            skill_config = self.skill_manager.get_skill(skill_name)
            if not skill_config:
                return {"error": f"Skill '{skill_name}' not found"}
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

    def execute_with_pause(
        self,
        agent_name: str,
        input_data: Dict,
        context: ExecutionContext
    ) -> Dict:
        """
        执行 agent，支持在需要时暂停等待用户输入

        Args:
            agent_name: agent 名称
            input_data: 输入数据
            context: 执行上下文

        Returns:
            执行结果，包含是否需要等待用户输入的标志
        """
        result = self.execute_agent(agent_name, input_data, context)

        # 检查是否有 ask_user 任务
        task_results = result.get("task_results", [])
        for tr in task_results:
            if tr.get("type") == "ask_user" and tr.get("needs_input"):
                result["needs_user_input"] = True
                result["pending_question"] = tr.get("question")
                result["question_reasoning"] = tr.get("reasoning", "")
                break

        return result

    def resume_after_user_input(
        self,
        agent_name: str,
        user_input: str,
        context: ExecutionContext,
        previous_question: str = ""
    ) -> Dict:
        """
        在用户输入后恢复执行

        Args:
            agent_name: agent 名称
            user_input: 用户输入
            context: 执行上下文
            previous_question: 之前的问题

        Returns:
            执行结果
        """
        # 将用户输入和之前的问题组合
        if previous_question:
            combined_input = f"Previous question: {previous_question}\nUser answer: {user_input}"
        else:
            combined_input = user_input

        # 添加到上下文
        context.add_message("user", combined_input)

        # 继续执行
        input_data = {"query": combined_input}
        return self.execute_agent(agent_name, input_data, context)

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
        has_error = False

        for result in task_results:
            if result["type"] == "skill":
                skill_result = result["result"]
                if "error" not in skill_result:
                    # 如果 skill 返回了直接的 result 字段，直接使用
                    if "result" in skill_result:
                        results_text.append(
                            f"## Skill Result: {result['name']}\n{skill_result['result']}"
                        )
                    else:
                        # 成功的 skill 结果
                        results_text.append(
                            f"## Skill Result: {result['name']}\n"
                            f"```json\n{json.dumps(skill_result, ensure_ascii=False, indent=2)}\n```"
                        )
                else:
                    # Skill 执行失败
                    has_error = True
                    error_msg = skill_result.get("error", "Unknown error")
                    logger.warning(f"Skill {result['name']} failed: {error_msg}")
                    # 添加错误信息，让 LLM 知道
                    results_text.append(
                        f"## Skill {result['name']} unavailable\n"
                        f"Note: {error_msg}\n"
                    )
            elif result["type"] == "agent":
                agent_result = result["result"]
                response_text = agent_result.get('response', '')
                results_text.append(
                    f"## Agent Result: {result['name']}\n"
                    f"{response_text[:1000]}"
                )
            elif result["type"] == "ask_user":
                # 有追问，直接返回追问内容
                question = result["question"]
                reasoning = result.get("reasoning", "")
                return f"{reasoning}\n\n{question}" if reasoning else question
            elif result["type"] == "error":
                has_error = True
                results_text.append(f"## Error\n{result.get('error', 'Unknown error')}")

        # 如果没有有效结果，返回原始响应
        if not results_text:
            return original_response

        # 构建提示，让 LLM 基于结果生成响应
        prompt_messages = list(messages)

        # 如果有错误，添加说明
        if has_error:
            instruction = (
                "Some skills were unavailable. Please provide a helpful response to the user "
                "based on your knowledge, even without the skill results. You can suggest "
                "appropriate statistical methods and provide code examples."
            )
        else:
            instruction = "Based on the skill/agent execution results above, please provide your response to the user."

        prompt_messages.append({
            "role": "user",
            "content": f"{instruction}\n\n## Execution Results:\n" + "\n".join(results_text)
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
