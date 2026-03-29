"""
Agent 文件管理器

动态生成和管理 Claude Code 格式的 agent 文件 (Markdown + YAML frontmatter)
"""
import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from config import get_config
from utils.logger import get_logger

logger = get_logger(__name__)


class AgentManager:
    """Agent 文件管理器 - 管理 Claude Code 格式的 agent 文件"""

    def __init__(self, registry_dir: str = None, config_path: str = None):
        """
        初始化 Agent 管理器

        Args:
            registry_dir: agent 文件注册目录
            config_path: agent 配置文件路径
        """
        cfg = get_config().registry
        self.registry_dir = Path(registry_dir or cfg.agents_dir)
        self.config_path = Path(config_path or cfg.agents_config)

        # 确保目录存在
        self.registry_dir.mkdir(parents=True, exist_ok=True)

        # 加载配置
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """加载 agent 配置文件"""
        if not self.config_path.exists():
            logger.warning(f"Agent config file not found: {self.config_path}")
            return {"agents": {}}

        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {"agents": {}}

    def _save_config(self) -> None:
        """保存 agent 配置文件"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False)

    def _render_agent_md(self, frontmatter: Dict, prompt: str) -> str:
        """
        渲染 agent Markdown 文件

        Args:
            frontmatter: YAML frontmatter 数据
            prompt: agent 提示词

        Returns:
            Markdown 文件内容
        """
        yaml_lines = ["---"]
        for key, value in frontmatter.items():
            if isinstance(value, list):
                yaml_lines.append(f"{key}: [{', '.join(str(v) for v in value)}]")
            elif isinstance(value, dict):
                yaml_lines.append(f"{key}: {yaml.dump(value, default_flow_style=True).strip()}")
            else:
                yaml_lines.append(f"{key}: {value}")
        yaml_lines.append("---")

        return "\n".join(yaml_lines) + "\n\n" + prompt.strip() + "\n"

    def _parse_agent_md(self, content: str) -> Dict:
        """
        解析 agent Markdown 文件

        Args:
            content: Markdown 文件内容

        Returns:
            agent 配置字典
        """
        lines = content.split('\n')
        frontmatter = {}
        prompt_start = 0

        # 解析 YAML frontmatter
        if lines and lines[0] == "---":
            i = 1
            while i < len(lines) and lines[i] != "---":
                line = lines[i].rstrip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    # 处理列表格式
                    if value.startswith('[') and value.endswith(']'):
                        value = [v.strip() for v in value[1:-1].split(',') if v.strip()]
                    frontmatter[key] = value
                i += 1
            prompt_start = i + 1

        # 提取 prompt
        prompt = '\n'.join(lines[prompt_start:]).strip()

        return {
            "frontmatter": frontmatter,
            "prompt": prompt
        }

    def register_agent(self, name: str, config: Dict) -> None:
        """
        从配置创建 agent 文件

        Args:
            name: agent 名称
            config: agent 配置
        """
        agent_path = self.registry_dir / f"{name}.md"

        frontmatter = {
            "name": config.get("name", name),
            "description": config.get("description", ""),
            "tools": config.get("tools", []),
            "model": config.get("model", "inherit"),
        }

        # 添加可选字段
        if "skills" in config:
            frontmatter["skills"] = config["skills"]
        if "max_turns" in config:
            frontmatter["max_turns"] = config["max_turns"]

        content = self._render_agent_md(frontmatter, config.get("prompt", ""))
        agent_path.write_text(content, encoding='utf-8')

        # 更新配置
        if "agents" not in self.config:
            self.config["agents"] = {}
        self.config["agents"][name] = config

        logger.info(f"Registered agent: {name} at {agent_path}")

    def get_agent(self, name: str) -> Optional[Dict]:
        """
        读取 agent 配置

        Args:
            name: agent 名称

        Returns:
            agent 配置字典，不存在则返回 None
        """
        agent_path = self.registry_dir / f"{name}.md"
        if not agent_path.exists():
            return None

        content = agent_path.read_text(encoding='utf-8')
        parsed = self._parse_agent_md(content)

        return {
            "name": name,
            "frontmatter": parsed["frontmatter"],
            "prompt": parsed["prompt"],
            "path": str(agent_path)
        }

    def list_agents(self) -> List[Dict]:
        """
        列出所有可用 agents

        Returns:
            agent 信息列表
        """
        agents = []
        for agent_file in self.registry_dir.glob("*.md"):
            name = agent_file.stem
            agent_info = self.get_agent(name)
            if agent_info:
                agents.append({
                    "name": name,
                    "description": agent_info["frontmatter"].get("description", ""),
                    "tools": agent_info["frontmatter"].get("tools", []),
                    "skills": agent_info["frontmatter"].get("skills", []),
                    "subagents": agent_info["frontmatter"].get("subagents", []),
                    "model": agent_info["frontmatter"].get("model", "inherit"),
                })
        return agents

    def delete_agent(self, name: str) -> bool:
        """
        删除 agent 文件

        Args:
            name: agent 名称

        Returns:
            是否成功删除
        """
        agent_path = self.registry_dir / f"{name}.md"
        if not agent_path.exists():
            return False

        agent_path.unlink()

        # 更新配置
        if "agents" in self.config and name in self.config["agents"]:
            del self.config["agents"][name]
            self._save_config()

        logger.info(f"Deleted agent: {name}")
        return True

    def reload_from_config(self) -> None:
        """从配置文件重新加载所有 agents"""
        if "agents" not in self.config:
            return

        for name, config in self.config["agents"].items():
            self.register_agent(name, config)

        logger.info(f"Reloaded {len(self.config['agents'])} agents from config")

    def update_agent(self, name: str, config: Dict) -> bool:
        """
        更新 agent 配置

        Args:
            name: agent 名称
            config: 新的配置

        Returns:
            是否成功更新
        """
        if name not in [a["name"] for a in self.list_agents()]:
            return False

        self.register_agent(name, config)
        logger.info(f"Updated agent: {name}")
        return True
