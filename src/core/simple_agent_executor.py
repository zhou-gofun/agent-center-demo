"""
简洁的 Agent 执行器

核心逻辑：
while not done:
    llm_response = llm.chat(messages)
    messages.append({"role": "assistant", "content": llm_response})

    tasks = parse_tasks(llm_response)
    if not tasks:
        break  # LLM 没有任务，任务完成

    results = execute_tasks(tasks)
    messages.append({"role": "user", "content": format_results(results)})
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Any

from core.execution_context import ExecutionContext
from core.task_parser import TaskParser, Task, ActionType
from core.llm_client import QwenClient
from core.agent_manager import AgentManager
from core.skill_manager import SkillManager
from core.universal_executor import get_universal_executor
from core.registry_scanner import get_scanner
from config import get_config
from utils.logger import get_logger

logger = get_logger(__name__)


class SimpleAgentExecutor:
    """简洁的 Agent 执行器"""

    def __init__(self):
        self.llm = QwenClient()
        self.task_parser = TaskParser()
        self.skill_manager = SkillManager()
        self.agent_manager = AgentManager()
        self.universal_executor = get_universal_executor()
        self.registry_scanner = get_scanner()
        self.cfg = get_config()

    def execute(
        self,
        agent_name: str,
        input_data: Dict,
        context: Optional[ExecutionContext] = None,
        max_iterations: int = 10
    ) -> Dict:
        """
        执行 Agent，直到任务完成或达到最大迭代

        核心循环：
        1. LLM 生成响应
        2. 解析任务
        3. 执行任务
        4. 将结果反馈给 LLM
        5. 重复直到没有任务

        Args:
            agent_name: agent 名称
            input_data: 输入数据
            context: 执行上下文
            max_iterations: 最大迭代次数

        Returns:
            执行结果
        """
        # 1. 创建或使用现有上下文
        if context is None:
            context = ExecutionContext()

        logger.info(f"[SimpleAgentExecutor] Executing agent: {agent_name}")

        # 2. 获取 agent 配置
        agent_config = self.agent_manager.get_agent(agent_name)
        if not agent_config:
            return {
                "success": False,
                "error": f"Agent '{agent_name}' not found",
                "agent": agent_name
            }

        # 3. 构建初始消息
        messages = self._build_messages(agent_config, input_data, context)

        # 4. 执行循环
        all_results = []
        final_response = ""

        for iteration in range(max_iterations):
            logger.info(f"[{agent_name}] Iteration {iteration + 1}/{max_iterations}")

            # LLM 响应
            llm_response = self.llm.chat(messages, temperature=0.3)
            if llm_response is None:
                llm_response = ""
                logger.warning(f"LLM returned None response for agent {agent_name}")

            # 添加到消息历史和上下文
            context.add_message("assistant", llm_response)
            messages.append({"role": "assistant", "content": llm_response})

            # 解析任务
            tasks = self.task_parser.parse(llm_response)
            logger.info(f"[{agent_name}] Parsed {len(tasks)} tasks: {tasks}")



            if not tasks:
                # LLM 没有生成任务，任务完成
                logger.info(f"[{agent_name}] No tasks generated, completion")
                final_response = llm_response
                break

            # 执行任务
            results = self._execute_tasks(tasks, input_data, context, agent_name)
            all_results.extend(results)
            logger.info(f"[{agent_name}] Executed tasks: {results}")



            # 格式化结果并添加到消息
            result_text = self._format_results(results)
            if result_text:
                messages.append({"role": "user", "content": result_text})
            else:
                # 没有结果，停止
                break

            # 检查是否所有任务都成功
            if self._all_success(results):
                # 检查是否需要继续（有些 skill 可能建议下一步操作）
                if self._should_continue(results):
                    # 继续循环
                    continue
                else:
                    # 任务完成
                    break

        # 如果没有最终响应，使用最后一次 LLM 响应
        if not final_response and all_results:
            # 生成最终响应
            final_response = self._generate_final_response(messages, all_results)
        elif not final_response:
            final_response = llm_response

        return {
            "success": True,
            "agent": agent_name,
            "response": final_response,
            "context": context.to_dict(),
            "tasks_executed": len(all_results),
            "task_results": all_results
        }

    def _build_messages(
        self,
        agent_config: Dict,
        input_data: Dict,
        context: ExecutionContext
    ) -> List[Dict]:
        """
        构建消息列表（包含技能列表）

        Args:
            agent_config: agent 配置
            input_data: 输入数据
            context: 执行上下文

        Returns:
            消息列表
        """
        # 构建系统提示
        system_prompt = agent_config["prompt"]

        # 添加技能列表
        preloaded_skills = agent_config["frontmatter"].get("skills", [])
        if not preloaded_skills:
            preloaded_skills = self.registry_scanner.list_skills()

        if preloaded_skills:
            # Agent frontmatter 中明确列出的技能：注入完整内容
            explicit_skills = agent_config["frontmatter"].get("skills", [])
            skill_sections = []

            for skill_name in preloaded_skills:
                skill_spec = self.registry_scanner.get_skill_spec(skill_name)
                if skill_spec:
                    # 对于明确列出的技能，注入完整内容
                    if skill_name in explicit_skills:
                        instructions = skill_spec.get("instructions", "")
                        skill_sections.append(f"""
## Skill: {skill_name}

{instructions}
---
""")
                    else:
                        # 其他技能只显示描述
                        desc = skill_spec["frontmatter"].get("description", "")
                        skill_sections.append(f"- **{skill_name}**: {desc}")

            if explicit_skills:
                # 有明确预加载的技能，注入完整内容
                skills_content = "\n".join(skill_sections)
                system_prompt = f"""## Preloaded Skills
The following skills are preloaded with full content:

{skills_content}

**How to use a skill:**
When you need to use a skill, format your response as:
```json
{{
  "skill": "skill_name",
  "action": "execute",
  "input": {{...}}
}}
```

{system_prompt}"""
            else:
                # 没有明确预加载的技能，只显示列表
                skills_section = "\n".join(skill_sections)
                system_prompt = f"""## Available Skills
You have access to the following skills:

{skills_section}

**How to use a skill:**
When you need to use a skill, format your response as:
```json
{{
  "skill": "skill_name",
  "action": "execute",
  "input": {{...}}
}}
```

{system_prompt}"""

        # 构建消息
        messages = [{"role": "system", "content": system_prompt}]

        # 添加上下文历史
        if context.conversation_history:
            messages.extend(context.conversation_history)

        # 添加当前输入
        user_message = self._format_input(input_data)
        messages.append({"role": "user", "content": user_message})

        return messages

    def _execute_tasks(
        self,
        tasks: List[Task],
        input_data: Dict,
        context: ExecutionContext,
        agent_name: str
    ) -> List[Dict]:
        """
        执行任务列表

        Args:
            tasks: 任务列表
            input_data: 输入数据
            context: 执行上下文
            agent_name: 当前 agent 名称

        Returns:
            执行结果列表
        """
        results = []

        for task in tasks:
            try:
                if task.action == ActionType.USE_SKILL:
                    result = self._execute_skill(task, input_data, context)
                    results.append({
                        "type": "skill",
                        "name": task.data.get("skill", "unknown"),
                        "result": result
                    })
                elif task.action == ActionType.DELEGATE_TO_AGENT:
                    result = self._execute_agent_delegation(task, input_data, context)
                    results.append({
                        "type": "agent",
                        "name": task.data.get("agent", "unknown"),
                        "result": result
                    })
                elif task.action == ActionType.ASK_USER:
                    results.append({
                        "type": "ask_user",
                        "question": task.data.get("question"),
                        "reasoning": task.data.get("reasoning", ""),
                        "needs_input": True
                    })
                else:
                    logger.warning(f"Unknown action type: {task.action}")
            except Exception as e:
                logger.error(f"Error executing task {task.action}: {e}")
                results.append({
                    "type": "error",
                    "error": str(e)
                })

        return results

    def _execute_skill(
        self,
        task: Task,
        input_data: Dict,
        context: ExecutionContext
    ) -> Dict:
        """
        执行 skill

        Args:
            task: 任务对象
            input_data: 输入数据
            context: 执行上下文

        Returns:
            执行结果
        """
        skill_name = task.data.get("skill")
        skill_input = task.data.get("input", {})

        logger.info(f"Executing skill: {skill_name}")

        # 获取 skill spec
        skill_spec = self.registry_scanner.get_skill_spec(skill_name)
        if not skill_spec:
            return {"error": f"Skill '{skill_name}' not found in registry"}

        # 检查执行配置
        execution_config = skill_spec.get("execution", {})
        exec_type = execution_config.get("type", "llm")

        if exec_type == "script":
            # 使用通用脚本执行器
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
                skill_name, skill_config, skill_input, context
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

    def _execute_agent_delegation(
        self,
        task: Task,
        input_data: Dict,
        parent_context: ExecutionContext
    ) -> Dict:
        """
        委派给 subagent

        Args:
            task: 任务对象
            input_data: 输入数据
            parent_context: 父上下文

        Returns:
            执行结果
        """
        agent_name = task.data.get("agent")
        context_type = task.data.get("context", "inherit")
        agent_input = task.data.get("input", {})

        # 合并输入数据
        merged_input = {**input_data, **agent_input}

        # 创建子上下文
        if context_type == "fork":
            child_context = parent_context.create_fork()
        else:
            child_context = parent_context.create_inherit()

        # 执行 agent（递归调用自身）
        result = self.execute(agent_name, merged_input, child_context)

        return {
            "agent": agent_name,
            "context_type": context_type,
            "response": result.get("response"),
            "context": result.get("context")
        }

    def _format_results(self, results: List[Dict]) -> str:
        """
        格式化执行结果

        Args:
            results: 执行结果列表

        Returns:
            格式化的结果文本
        """
        if not results:
            return ""

        formatted = []
        for i, result in enumerate(results, 1):
            result_type = result.get("type", "unknown")

            if result_type == "skill":
                name = result.get("name", "unknown")
                skill_result = result.get("result", {})

                if isinstance(skill_result, dict):
                    if "error" in skill_result:
                        formatted.append(f"{i}. Skill '{name}' FAILED: {skill_result['error']}")
                    elif "image_path" in skill_result:
                        formatted.append(f"{i}. Skill '{name}' generated image: {skill_result['image_path']}")
                    elif "result" in skill_result:
                        result_text = str(skill_result['result'])
                        if len(result_text) > 500:
                            result_text = result_text[:500] + "..."
                        formatted.append(f"{i}. Skill '{name}' result: {result_text}")
                    else:
                        # 显示其他关键字段
                        key_info = {k: v for k, v in skill_result.items() if k not in ["data_file", "data_info"]}
                        json_str = json.dumps(key_info, ensure_ascii=False)[:500]
                        formatted.append(f"{i}. Skill '{name}' completed: {json_str}")
                else:
                    result_text = str(skill_result)[:500]
                    formatted.append(f"{i}. Skill '{name}' completed: {result_text}")

            elif result_type == "agent":
                name = result.get("name", "unknown")
                agent_result = result.get("result", {})
                response = agent_result.get("response") or ""
                response_text = response[:500] if len(response) > 500 else response
                formatted.append(f"{i}. Agent '{name}' response: {response_text}")

            elif result_type == "ask_user":
                formatted.append(f"{i}. Question for user: {result.get('question')}")

            elif result_type == "error":
                formatted.append(f"{i}. Error: {result.get('error', 'Unknown error')}")

        if not formatted:
            return ""

        return f"Skill execution results:\n" + "\n".join(formatted) + "\n\nPlease evaluate:\n1. Is the user's request satisfied?\n2. If not, what should be done next?\n\nIf you need to execute more skills, respond with another skill call. Otherwise, provide your final answer to the user."

    def _all_success(self, results: List[Dict]) -> bool:
        """检查是否所有任务都成功"""
        for result in results:
            result_type = result.get("type", "")
            if result_type == "skill":
                if "error" in result.get("result", {}):
                    return False
            elif result_type == "error":
                return False
        return True

    def _should_continue(self, results: List[Dict]) -> bool:
        """检查是否应该继续执行"""
        for result in results:
            result_type = result.get("type", "")
            if result_type == "ask_user":
                # 需要用户输入，停止
                return False
            if result_type == "skill":
                skill_result = result.get("result", {})
                # 检查是否有建议的下一步操作
                if isinstance(skill_result, dict):
                    if "suggested_analysis" in skill_result or "matched_tools" in skill_result:
                        # 有建议的操作，继续
                        return True
        return False

    def _generate_final_response(self, messages: List[Dict], task_results: List[Dict]) -> str:
        """
        基于任务执行结果生成最终响应

        Args:
            messages: 消息历史
            task_results: 任务执行结果

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
                    if "result" in skill_result:
                        results_text.append(
                            f"## Skill Result: {result['name']}\n{skill_result['result']}"
                        )
                    else:
                        results_text.append(
                            f"## Skill Result: {result['name']}\n"
                            f"```json\n{json.dumps(skill_result, ensure_ascii=False, indent=2)}\n```"
                        )
                else:
                    has_error = True
                    error_msg = skill_result.get("error", "Unknown error")
                    results_text.append(
                        f"## Skill {result['name']} unavailable\nNote: {error_msg}\n"
                    )
            elif result["type"] == "agent":
                agent_result = result["result"]
                response_text = agent_result.get('response') or ''
                results_text.append(
                    f"## Agent Result: {result['name']}\n{response_text[:1000]}"
                )
            elif result["type"] == "ask_user":
                question = result["question"]
                reasoning = result.get("reasoning", "")
                return f"{reasoning}\n\n{question}" if reasoning else question
            elif result["type"] == "error":
                has_error = True
                results_text.append(f"## Error\n{result.get('error', 'Unknown error')}")

        if not results_text:
            return ""

        # 构建提示
        if has_error:
            instruction = (
                "Some skills were unavailable. Please provide a helpful response to the user "
                "based on your knowledge, even without the skill results. You can suggest "
                "appropriate methods and provide code examples."
            )
        else:
            instruction = "Based on the skill/agent execution results above, please provide your response to the user."

        prompt_messages = list(messages)
        prompt_messages.append({
            "role": "user",
            "content": f"{instruction}\n\n## Execution Results:\n" + "\n".join(results_text)
        })

        try:
            return self.llm.chat(prompt_messages, temperature=0.3)
        except Exception as e:
            logger.error(f"Error generating final response: {e}")
            return ""

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
_executor = None


def get_simple_executor() -> SimpleAgentExecutor:
    """获取简洁执行器实例"""
    global _executor
    if _executor is None:
        _executor = SimpleAgentExecutor()
    return _executor
