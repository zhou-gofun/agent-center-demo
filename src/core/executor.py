"""
Agent/Skill 执行引擎

模拟 Claude Code 的 agent 执行机制

集成新的编排系统：
- ExecutionContext: 上下文隔离
- TaskParser: 任务解析
- ExecutionOrchestrator: 执行编排
- ConversationalLoop: 对话循环
- RegistryScanner: 动态扫描 skills/agents
- UniversalScriptExecutor: 通用脚本执行器
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from core.llm_client import QwenClient, AsyncQwenClient
from core.agent_manager import AgentManager
from core.skill_manager import SkillManager
from core.universal_executor import get_universal_executor
from core.registry_scanner import get_scanner
from config import get_config
from utils.logger import get_logger

# 新的编排系统
from core.execution_context import ExecutionContext
from core.task_parser import TaskParser
from core.execution_orchestrator import ExecutionOrchestrator, get_orchestrator
from core.python_script_executor import PythonScriptExecutor

logger = get_logger(__name__)


class ToolCall:
    """工具调用表示"""

    def __init__(self, name: str, arguments: Dict[str, Any]):
        self.name = name
        self.arguments = arguments

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "arguments": self.arguments
        }


class ExecutionResult:
    """执行结果"""

    def __init__(
        self,
        success: bool,
        agent: str,
        response: str,
        tool_calls: List[ToolCall] = None,
        metadata: Dict = None
    ):
        self.success = success
        self.agent = agent
        self.response = response
        self.tool_calls = tool_calls or []
        self.metadata = metadata or {}
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "agent": self.agent,
            "response": self.response,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


class AgentExecutor:
    """Agent 执行引擎 - 模拟 Claude Code 的 agent 执行"""

    def __init__(self, llm_client: QwenClient = None, agent_manager: AgentManager = None):
        """
        初始化执行引擎

        Args:
            llm_client: LLM 客户端
            agent_manager: Agent 管理器
        """
        self.llm = llm_client or QwenClient()
        self.agent_manager = agent_manager or AgentManager()
        self.skill_manager = SkillManager()
        self.universal_executor = get_universal_executor()
        self.registry_scanner = get_scanner()
        self.cfg = get_config()

    def _format_input(self, input_data: Dict) -> str:
        """格式化输入数据为提示文本"""
        if "query" in input_data:
            return input_data["query"]
        if "prompt" in input_data:
            return input_data["prompt"]
        return json.dumps(input_data, ensure_ascii=False, indent=2)

    def _extract_skill_request(self, response: str) -> Optional[Dict]:
        """
        从响应中提取 skill 请求

        解析格式：
        ```json
        {
          "skill": "skill_name",
          "action": "execute",
          "reasoning": "..."
        }
        ```
        """
        try:
            # 尝试提取 JSON 代码块
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
                data = json.loads(json_str)
                if "skill" in data:
                    return {
                        "skill": data["skill"],
                        "action": data.get("action", "execute"),
                        "input": data.get("input", {}),
                        "reasoning": data.get("reasoning", "")
                    }
            # 尝试直接解析 JSON
            lines = response.strip().split('\n')
            for i, line in enumerate(lines):
                if line.strip().startswith('{'):
                    json_str = '\n'.join(lines[i:])
                    # 确保有闭合括号
                    brace_count = 0
                    end_pos = 0
                    for j, char in enumerate(json_str):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_pos = j + 1
                                break
                    if end_pos > 0:
                        json_str = json_str[:end_pos]
                        data = json.loads(json_str)
                        if "skill" in data:
                            return {
                                "skill": data["skill"],
                                "action": data.get("action", "execute"),
                                "reasoning": data.get("reasoning", "")
                            }
        except (json.JSONDecodeError, KeyError, ValueError):
            pass
        return None

    def _extract_tool_calls(self, response: str) -> List[ToolCall]:
        """
        从响应中提取工具调用

        解析类似 <function_calls>...</function_calls> 的格式
        """
        tool_calls = []

        # 简单实现：检测 JSON 格式的工具调用
        # 实际中需要更复杂的解析逻辑
        try:
            if "```json" in response:
                # 提取代码块中的 JSON
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
                data = json.loads(json_str)
                if "tool_calls" in data:
                    for tc in data["tool_calls"]:
                        tool_calls.append(ToolCall(tc["name"], tc.get("arguments", {})))
            elif "<function_calls>" in response:
                # 解析 function_calls 标签
                start = response.find("<function_calls>") + 16
                end = response.find("</function_calls>")
                content = response[start:end].strip()
                data = json.loads(content)
                if isinstance(data, list):
                    for tc in data:
                        tool_calls.append(ToolCall(tc["name"], tc.get("arguments", {})))
                elif isinstance(data, dict) and "name" in data:
                    tool_calls.append(ToolCall(data["name"], data.get("arguments", {})))
        except (json.JSONDecodeError, KeyError) as e:
            logger.debug(f"Failed to parse tool calls: {e}")

        return tool_calls

    def execute_agent(self, agent_name: str, input_data: Dict) -> ExecutionResult:
        """
        执行指定的 agent

        Args:
            agent_name: agent 名称
            input_data: 输入数据

        Returns:
            执行结果
        """
        agent_config = self.agent_manager.get_agent(agent_name)
        if not agent_config:
            return ExecutionResult(
                success=False,
                agent=agent_name,
                response=f"Agent '{agent_name}' not found",
                metadata={"error": "agent_not_found"}
            )

        try:
            # 构建系统提示
            system_prompt = agent_config["prompt"]

            # 获取可用 skills（支持自动发现）
            available_skills = agent_config["frontmatter"].get("skills", [])

            # 如果 agent 没有配置 skills 列表，自动获取所有可用 skills
            if not available_skills:
                available_skills = self.registry_scanner.list_skills()

            if available_skills:
                # 构建 skills 描述（包含 name 和 description）
                skill_descriptions = []
                for skill_name in available_skills:
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

            # 构建消息
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": self._format_input(input_data)}
            ]

            # 调用 LLM
            response = self.llm.chat(messages, temperature=0.3)

            # 检查是否请求了 skill
            skill_request = self._extract_skill_request(response)
            if skill_request and skill_request["skill"] in available_skills:
                # 执行请求的 skill（使用 skill 特定的 input）
                skill_input = skill_request.get("input", {})
                skill_result = self._execute_python_skill(skill_request["skill"], skill_input)
                if skill_result and "error" not in skill_result:
                    # 如果 skill 返回了直接的 result 字段，直接使用
                    if "result" in skill_result:
                        response = skill_result["result"]
                    else:
                        # 将 skill 结果添加到上下文，再次调用 LLM
                        skill_context = f"\n\n## Skill Result: {skill_request['skill']}\n```json\n{json.dumps(skill_result, ensure_ascii=False, indent=2)}\n```\n\nPlease provide your response based on this skill result."
                        messages.append({"role": "assistant", "content": response})
                        messages.append({"role": "user", "content": skill_context})
                        response = self.llm.chat(messages, temperature=0.3)

            # 提取工具调用
            tool_calls = self._extract_tool_calls(response)

            metadata = {
                "model": self.llm.model,
                "agent_config": {
                    "description": agent_config["frontmatter"].get("description", ""),
                    "tools": agent_config["frontmatter"].get("tools", []),
                    "skills": available_skills
                }
            }

            return ExecutionResult(
                success=True,
                agent=agent_name,
                response=response,
                tool_calls=tool_calls,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Error executing agent {agent_name}: {e}")
            return ExecutionResult(
                success=False,
                agent=agent_name,
                response=f"Execution error: {str(e)}",
                metadata={"error": str(e)}
            )

    def _has_python_impl(self, skill_name: str) -> bool:
        """检查技能是否有脚本执行配置"""
        return self.registry_scanner.has_script_execution(skill_name)

    def _execute_python_skill(self, skill_name: str, input_data: Dict) -> Optional[Dict]:
        """执行Python技能实现（使用 UniversalScriptExecutor）"""
        if not self._has_python_impl(skill_name):
            return None

        skill_spec = self.registry_scanner.get_skill_spec(skill_name)
        if not skill_spec:
            return {"error": f"Skill '{skill_name}' not found in registry"}

        execution_config = skill_spec.get("execution", {})
        skill_dir = Path(self.cfg.registry.skills_dir) / skill_name

        return self.universal_executor.execute_skill(
            skill_name=skill_name,
            skill_dir=skill_dir,
            execution_config=execution_config,
            input_data=input_data
        )

    def _build_skill_context(self, skill_names: List[str], input_data: Dict = None) -> str:
        """构建技能上下文，执行Python技能并包含结果"""
        contexts = []

        for skill_name in skill_names:
            skill = self.skill_manager.get_skill(skill_name)
            if not skill:
                continue

            # 如果有Python实现，执行并包含结果
            if input_data is not None and self._has_python_impl(skill_name):
                python_result = self._execute_python_skill(skill_name, input_data)
                if python_result and "error" not in python_result:
                    # 将Python结果格式化为上下文
                    formatted_result = json.dumps(python_result, ensure_ascii=False, indent=2)
                    contexts.append(f"## Skill: {skill_name} (执行结果)\n```json\n{formatted_result}\n```")
                    logger.info(f"Executed Python skill: {skill_name}")
                else:
                    # Python执行失败，回退到指令
                    contexts.append(f"## Skill: {skill_name}\n{skill['instructions']}")
            else:
                # 没有Python实现，使用指令
                contexts.append(f"## Skill: {skill_name}\n{skill['instructions']}")

        return "\n\n".join(contexts)

    def execute_skill(self, skill_name: str, input_data: Dict) -> ExecutionResult:
        """
        执行指定的 skill

        Args:
            skill_name: skill 名称
            input_data: 输入数据

        Returns:
            执行结果
        """
        skill_config = self.skill_manager.get_skill(skill_name)
        if not skill_config:
            return ExecutionResult(
                success=False,
                agent=f"skill:{skill_name}",
                response=f"Skill '{skill_name}' not found",
                metadata={"error": "skill_not_found"}
            )

        try:
            # 构建系统提示
            system_prompt = skill_config["instructions"]

            # 添加工具上下文
            allowed_tools = skill_config["frontmatter"].get("allowed-tools", [])
            if allowed_tools:
                tool_context = f"Available tools: {', '.join(allowed_tools)}"
                system_prompt = f"{tool_context}\n\n{system_prompt}"

            # 构建消息
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": self._format_input(input_data)}
            ]

            # 调用 LLM
            response = self.llm.chat(messages, temperature=0.3)

            metadata = {
                "model": self.llm.model,
                "skill_config": {
                    "description": skill_config["frontmatter"].get("description", ""),
                    "allowed-tools": allowed_tools
                }
            }

            return ExecutionResult(
                success=True,
                agent=f"skill:{skill_name}",
                response=response,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Error executing skill {skill_name}: {e}")
            return ExecutionResult(
                success=False,
                agent=f"skill:{skill_name}",
                response=f"Execution error: {str(e)}",
                metadata={"error": str(e)}
            )

    def execute_agent_with_context(
        self,
        agent_name: str,
        input_data: Dict,
        context: Optional[ExecutionContext] = None,
        use_orchestrator: bool = True
    ) -> ExecutionResult:
        """
        使用新编排系统执行 agent（支持上下文隔离）

        Args:
            agent_name: agent 名称
            input_data: 输入数据
            context: 执行上下文
            use_orchestrator: 是否使用新的编排系统

        Returns:
            执行结果
        """
        if not use_orchestrator:
            # 回退到旧的执行方式
            return self.execute_agent(agent_name, input_data)

        try:
            orchestrator = get_orchestrator()
            result = orchestrator.execute_agent(agent_name, input_data, context)

            if result.get("success"):
                return ExecutionResult(
                    success=True,
                    agent=agent_name,
                    response=result.get("response", ""),
                    metadata={
                        "context": result.get("context"),
                        "tasks_executed": result.get("tasks_executed", 0)
                    }
                )
            else:
                return ExecutionResult(
                    success=False,
                    agent=agent_name,
                    response=result.get("error", "Unknown error"),
                    metadata={"error": result.get("error")}
                )

        except Exception as e:
            logger.error(f"Error in orchestrated execution: {e}")
            # 回退到旧的执行方式
            return self.execute_agent(agent_name, input_data)


class AsyncAgentExecutor:
    """异步 Agent 执行引擎"""

    def __init__(self, llm_client: AsyncQwenClient = None, agent_manager: AgentManager = None):
        """
        初始化异步执行引擎

        Args:
            llm_client: 异步 LLM 客户端
            agent_manager: Agent 管理器
        """
        self.llm = llm_client or AsyncQwenClient()
        self.agent_manager = agent_manager or AgentManager()
        self.skill_manager = SkillManager()
        self.universal_executor = get_universal_executor()
        self.registry_scanner = get_scanner()
        self.cfg = get_config()

    async def execute_agent(self, agent_name: str, input_data: Dict) -> ExecutionResult:
        """异步执行指定的 agent"""
        agent_config = self.agent_manager.get_agent(agent_name)
        if not agent_config:
            return ExecutionResult(
                success=False,
                agent=agent_name,
                response=f"Agent '{agent_name}' not found",
                metadata={"error": "agent_not_found"}
            )

        try:
            system_prompt = agent_config["prompt"]

            # 获取可用 skills（支持自动发现）
            available_skills = agent_config["frontmatter"].get("skills", [])

            # 如果 agent 没有配置 skills 列表，自动获取所有可用 skills
            if not available_skills:
                available_skills = self.registry_scanner.list_skills()

            if available_skills:
                # 构建 skills 描述（包含 name 和 description）
                skill_descriptions = []
                for skill_name in available_skills:
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

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": self._format_input(input_data)}
            ]

            response = await self.llm.chat(messages, temperature=0.3)

            # 检查是否请求了 skill
            skill_request = self._extract_skill_request(response)
            if skill_request and skill_request["skill"] in available_skills:
                # 执行请求的 skill（使用 skill 特定的 input）
                skill_input = skill_request.get("input", {})
                skill_result = await self._async_execute_python_skill(skill_request["skill"], skill_input)
                if skill_result and "error" not in skill_result:
                    # 如果 skill 返回了直接的 result 字段，直接使用
                    if "result" in skill_result:
                        response = skill_result["result"]
                    else:
                        # 将 skill 结果添加到上下文，再次调用 LLM
                        skill_context = f"\n\n## Skill Result: {skill_request['skill']}\n```json\n{json.dumps(skill_result, ensure_ascii=False, indent=2)}\n```\n\nPlease provide your response based on this skill result."
                        messages.append({"role": "assistant", "content": response})
                        messages.append({"role": "user", "content": skill_context})
                        response = await self.llm.chat(messages, temperature=0.3)

            return ExecutionResult(
                success=True,
                agent=agent_name,
                response=response,
                metadata={"model": self.llm.model, "skills": available_skills}
            )

        except Exception as e:
            logger.error(f"Error executing agent {agent_name}: {e}")
            return ExecutionResult(
                success=False,
                agent=agent_name,
                response=f"Execution error: {str(e)}",
                metadata={"error": str(e)}
            )

    def _has_python_impl(self, skill_name: str) -> bool:
        """检查技能是否有脚本执行配置"""
        return self.registry_scanner.has_script_execution(skill_name)

    def _execute_python_skill(self, skill_name: str, input_data: Dict) -> Optional[Dict]:
        """执行Python技能实现（使用 UniversalScriptExecutor）"""
        if not self._has_python_impl(skill_name):
            return None

        skill_spec = self.registry_scanner.get_skill_spec(skill_name)
        if not skill_spec:
            return {"error": f"Skill '{skill_name}' not found in registry"}

        execution_config = skill_spec.get("execution", {})
        skill_dir = Path(self.cfg.registry.skills_dir) / skill_name

        return self.universal_executor.execute_skill(
            skill_name=skill_name,
            skill_dir=skill_dir,
            execution_config=execution_config,
            input_data=input_data
        )

    def _build_skill_context(self, skill_names: List[str], input_data: Dict = None) -> str:
        """构建技能上下文，执行Python技能并包含结果"""
        contexts = []

        for skill_name in skill_names:
            skill = self.skill_manager.get_skill(skill_name)
            if not skill:
                continue

            # 如果有Python实现，执行并包含结果
            if input_data is not None and self._has_python_impl(skill_name):
                python_result = self._execute_python_skill(skill_name, input_data)
                if python_result and "error" not in python_result:
                    # 将Python结果格式化为上下文
                    formatted_result = json.dumps(python_result, ensure_ascii=False, indent=2)
                    contexts.append(f"## Skill: {skill_name} (执行结果)\n```json\n{formatted_result}\n```")
                    logger.info(f"Executed Python skill: {skill_name}")
                else:
                    # Python执行失败，回退到指令
                    contexts.append(f"## Skill: {skill_name}\n{skill['instructions']}")
            else:
                # 没有Python实现，使用指令
                contexts.append(f"## Skill: {skill_name}\n{skill['instructions']}")

        return "\n\n".join(contexts)

    def _format_input(self, input_data: Dict) -> str:
        """格式化输入数据为提示文本"""
        if "query" in input_data:
            return input_data["query"]
        if "prompt" in input_data:
            return input_data["prompt"]
        return json.dumps(input_data, ensure_ascii=False, indent=2)

    def _extract_skill_request(self, response: str) -> Optional[Dict]:
        """从响应中提取 skill 请求"""
        try:
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
                data = json.loads(json_str)
                if "skill" in data:
                    return {
                        "skill": data["skill"],
                        "action": data.get("action", "execute"),
                        "input": data.get("input", {}),
                        "reasoning": data.get("reasoning", "")
                    }
            lines = response.strip().split('\n')
            for i, line in enumerate(lines):
                if line.strip().startswith('{'):
                    json_str = '\n'.join(lines[i:])
                    brace_count = 0
                    end_pos = 0
                    for j, char in enumerate(json_str):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_pos = j + 1
                                break
                    if end_pos > 0:
                        json_str = json_str[:end_pos]
                        data = json.loads(json_str)
                        if "skill" in data:
                            return {
                                "skill": data["skill"],
                                "action": data.get("action", "execute"),
                                "reasoning": data.get("reasoning", "")
                            }
        except (json.JSONDecodeError, KeyError, ValueError):
            pass
        return None

    async def _async_execute_python_skill(self, skill_name: str, input_data: Dict) -> Optional[Dict]:
        """异步执行Python技能实现"""
        # 简化版本：同步调用，因为技能执行通常是同步的
        return self._execute_python_skill(skill_name, input_data)


def get_executor() -> AgentExecutor:
    """获取执行引擎实例"""
    return AgentExecutor()
