"""
执行上下文管理

实现 Subagent 上下文隔离机制
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ExecutionContext:
    """
    执行上下文

    支持上下文隔离（fork）和上下文继承（inherit）
    """

    # 上下文标识符
    context_id: str = ""

    # 父上下文（用于追溯）
    parent: Optional['ExecutionContext'] = None

    # 是否隔离（True: 不继承对话历史，False: 继承）
    isolated: bool = False

    # 对话历史
    conversation_history: List[Dict[str, str]] = field(default_factory=list)

    # 预加载的 skills
    preloaded_skills: List[str] = field(default_factory=list)

    # 预加载的 subagents
    preloaded_subagents: List[str] = field(default_factory=list)

    # 上下文变量
    variables: Dict[str, Any] = field(default_factory=dict)

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理"""
        if not self.context_id:
            import uuid
            self.context_id = str(uuid.uuid4())[:8]

    def create_fork(self) -> 'ExecutionContext':
        """
        创建隔离的子上下文

        子上下文不继承对话历史，但保留预加载的 skills/subagents
        """
        return ExecutionContext(
            parent=self,
            isolated=True,
            conversation_history=[],  # 隔离：空历史
            preloaded_skills=list(self.preloaded_skills),
            preloaded_subagents=list(self.preloaded_subagents),
            variables={},  # 隔离：空的变量
        )

    def create_inherit(self) -> 'ExecutionContext':
        """
        创建继承的子上下文

        子上下文继承对话历史和变量
        """
        return ExecutionContext(
            parent=self,
            isolated=False,
            conversation_history=list(self.conversation_history),
            preloaded_skills=list(self.preloaded_skills),
            preloaded_subagents=list(self.preloaded_subagents),
            variables=dict(self.variables),
        )

    def add_message(self, role: str, content: str):
        """添加消息到对话历史"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })

    def get_messages(self) -> List[Dict[str, str]]:
        """获取对话历史"""
        return self.conversation_history

    def set_variable(self, key: str, value: Any):
        """设置上下文变量"""
        self.variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        """获取上下文变量"""
        return self.variables.get(key, default)

    def preload_skill(self, skill_name: str):
        """预加载 skill"""
        if skill_name not in self.preloaded_skills:
            self.preloaded_skills.append(skill_name)

    def preload_subagent(self, agent_name: str):
        """预加载 subagent"""
        if agent_name not in self.preloaded_subagents:
            self.preloaded_subagents.append(agent_name)

    def has_skill(self, skill_name: str) -> bool:
        """检查是否有该 skill"""
        return skill_name in self.preloaded_skills

    def has_subagent(self, agent_name: str) -> bool:
        """检查是否有该 subagent"""
        return agent_name in self.preloaded_subagents

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "context_id": self.context_id,
            "isolated": self.isolated,
            "message_count": len(self.conversation_history),
            "preloaded_skills": self.preloaded_skills,
            "preloaded_subagents": self.preloaded_subagents,
            "variables": list(self.variables.keys()),
        }
