"""
任务解析器

从 LLM 响应中解析技能调用、Subagent 调用、用户追问等
"""
import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class ActionType(Enum):
    """动作类型"""
    USE_SKILL = "use_skill"
    DELEGATE_TO_AGENT = "delegate_to_agent"
    ASK_USER = "ask_user"
    MULTI_STEP = "multi_step"
    DIRECT_RESPONSE = "direct_response"


@dataclass
class Task:
    """解析出的任务"""
    action: ActionType
    data: Dict[str, Any]
    reasoning: str = ""

    def to_dict(self) -> Dict:
        return {
            "action": self.action.value,
            "data": self.data,
            "reasoning": self.reasoning
        }


class TaskParser:
    """
    任务解析器

    从 LLM 响应中解析各种任务指令
    """

    # Skill 调用格式
    SKILL_PATTERN = r'\{\s*"skill"\s*:\s*"([^"]+)"'

    # Subagent 调用格式
    AGENT_PATTERN = r'\{\s*"agent"\s*:\s*"([^"]+)"'

    # 用户追问格式
    ASK_USER_PATTERN = r'\{\s*"question"\s*:\s*"([^"]+)"'

    def __init__(self):
        self.parsers = [
            self._parse_multi_step,
            self._parse_skill_call,
            self._parse_agent_call,
            self._parse_ask_user,
        ]

    def parse(self, response: str) -> List[Task]:
        """
        解析响应，提取所有任务

        Args:
            response: LLM 响应文本

        Returns:
            任务列表
        """
        tasks = []

        # 尝试提取 JSON 代码块
        json_data = self._extract_json(response)

        if json_data:
            # 解析为单个任务或多步骤任务
            parsed = self._parse_json_task(json_data)
            if parsed:
                tasks.extend(parsed)
        else:
            # 尝试各个模式匹配
            for parser in self.parsers:
                result = parser(response)
                if result:
                    if isinstance(result, list):
                        tasks.extend(result)
                    else:
                        tasks.append(result)

        return tasks

    def _extract_json(self, response: str) -> Optional[Dict]:
        """提取 JSON 数据"""
        # 尝试提取 ```json 代码块
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试提取独立的 JSON 对象
        brace_match = self._extract_braced_json(response)
        if brace_match:
            try:
                return json.loads(brace_match)
            except json.JSONDecodeError:
                pass

        return None

    def _extract_braced_json(self, text: str) -> Optional[str]:
        """提取花括号包裹的 JSON"""
        lines = text.strip().split('\n')
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
                    return json_str[:end_pos]
        return None

    def _parse_json_task(self, data: Dict) -> List[Task]:
        """解析 JSON 格式的任务"""
        tasks = []

        # 检查是否是多步骤任务
        if data.get("action") == "multi_step" and "steps" in data:
            for step_data in data["steps"]:
                step_action = step_data.get("action")
                if step_action == "use_skill":
                    tasks.append(Task(
                        action=ActionType.USE_SKILL,
                        data={"skill": step_data.get("skill"), "input": step_data.get("input", {})},
                        reasoning=step_data.get("reasoning", "")
                    ))
                elif step_action == "delegate_to_agent":
                    tasks.append(Task(
                        action=ActionType.DELEGATE_TO_AGENT,
                        data={"agent": step_data.get("agent"), "context": step_data.get("context", "inherit"), "input": step_data.get("input", {})},
                        reasoning=step_data.get("reasoning", "")
                    ))
                elif step_action == "ask_user":
                    tasks.append(Task(
                        action=ActionType.ASK_USER,
                        data={"question": step_data.get("question"), "reasoning": step_data.get("reasoning", "")},
                        reasoning=step_data.get("reasoning", "")
                    ))
            return tasks

        # 单个任务
        if "skill" in data:
            return [Task(
                action=ActionType.USE_SKILL,
                data={"skill": data["skill"], "input": data.get("input", {})},
                reasoning=data.get("reasoning", "")
            )]

        if "agent" in data or "target" in data:
            agent_name = data.get("agent") or data.get("target")
            return [Task(
                action=ActionType.DELEGATE_TO_AGENT,
                data={"agent": agent_name, "context": data.get("context", "inherit"), "input": data.get("input", {})},
                reasoning=data.get("reasoning", "")
            )]

        if "question" in data:
            return [Task(
                action=ActionType.ASK_USER,
                data={"question": data["question"], "reasoning": data.get("reasoning", "")},
                reasoning=data.get("reasoning", "")
            )]

        return tasks

    def _parse_multi_step(self, response: str) -> Optional[List[Task]]:
        """解析多步骤任务（备用方法）"""
        if "action" not in response.lower() or "multi_step" not in response.lower():
            return None
        # 已在 _parse_json_task 中处理
        return None

    def _parse_skill_call(self, response: str) -> Optional[Task]:
        """解析 skill 调用"""
        json_data = self._extract_json(response)
        if json_data and "skill" in json_data:
            return Task(
                action=ActionType.USE_SKILL,
                data={"skill": json_data["skill"], "input": json_data.get("input", {})},
                reasoning=json_data.get("reasoning", "")
            )
        return None

    def _parse_agent_call(self, response: str) -> Optional[Task]:
        """解析 subagent 调用"""
        json_data = self._extract_json(response)
        if json_data and ("agent" in json_data or "target" in json_data):
            agent_name = json_data.get("agent") or json_data.get("target")
            if agent_name and agent_name != "direct_response":
                return Task(
                    action=ActionType.DELEGATE_TO_AGENT,
                    data={"agent": agent_name, "context": json_data.get("context", "inherit"), "input": json_data.get("input", {})},
                    reasoning=json_data.get("reasoning", "")
                )
        return None

    def _parse_ask_user(self, response: str) -> Optional[Task]:
        """解析用户追问"""
        json_data = self._extract_json(response)
        if json_data and "question" in json_data:
            return Task(
                action=ActionType.ASK_USER,
                data={"question": json_data["question"], "reasoning": json_data.get("reasoning", "")},
                reasoning=json_data.get("reasoning", "")
            )
        return None


# 便捷函数
def parse_tasks(response: str) -> List[Task]:
    """解析响应中的任务"""
    parser = TaskParser()
    return parser.parse(response)
