"""
Skill 文件管理器

动态生成和管理 Claude Code 格式的 skill 文件 (Markdown + YAML frontmatter)
"""
import os
import yaml
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from config import get_config
from utils.logger import get_logger

logger = get_logger(__name__)


class SkillManager:
    """Skill 文件管理器 - 管理 Claude Code 格式的 skill 文件"""

    def __init__(self, registry_dir: str = None, config_path: str = None):
        """
        初始化 Skill 管理器

        Args:
            registry_dir: skill 文件注册目录
            config_path: skill 配置文件路径
        """
        cfg = get_config().registry
        self.registry_dir = Path(registry_dir or cfg.skills_dir)
        self.config_path = Path(config_path or cfg.skills_config)

        # 确保目录存在
        self.registry_dir.mkdir(parents=True, exist_ok=True)

        # 加载配置
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """加载 skill 配置文件"""
        if not self.config_path.exists():
            logger.warning(f"Skill config file not found: {self.config_path}")
            return {"skills": {}}

        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {"skills": {}}

    def _save_config(self) -> None:
        """保存 skill 配置文件"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False)

    def _render_skill_md(self, frontmatter: Dict, instructions: str) -> str:
        """
        渲染 skill Markdown 文件

        Args:
            frontmatter: YAML frontmatter 数据
            instructions: skill 指令

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

        return "\n".join(yaml_lines) + "\n\n" + instructions.strip() + "\n"

    def _parse_skill_md(self, content: str) -> Dict:
        """
        解析 skill Markdown 文件

        Args:
            content: Markdown 文件内容

        Returns:
            skill 配置字典
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

        # 提取 instructions
        instructions = '\n'.join(lines[prompt_start:]).strip()

        return {
            "frontmatter": frontmatter,
            "instructions": instructions
        }

    def register_skill(self, name: str, config: Dict) -> None:
        """
        从配置创建 skill 文件

        Args:
            name: skill 名称
            config: skill 配置
        """
        skill_dir = self.registry_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_path = skill_dir / "SKILL.md"

        frontmatter = {
            "name": config.get("name", name),
            "description": config.get("description", ""),
            "allowed-tools": config.get("allowed-tools", []),
        }

        # 添加可选字段
        if "context" in config:
            frontmatter["context"] = config["context"]
        if "agent" in config:
            frontmatter["agent"] = config["agent"]

        content = self._render_skill_md(frontmatter, config.get("instructions", ""))
        skill_path.write_text(content, encoding='utf-8')

        # 复制支持文件
        support_files = config.get("support_files", [])
        for support_file in support_files:
            src_path = Path(support_file)
            if src_path.exists():
                shutil.copy(src_path, skill_dir / src_path.name)

        # 更新配置
        if "skills" not in self.config:
            self.config["skills"] = {}
        self.config["skills"][name] = config

        logger.info(f"Registered skill: {name} at {skill_path}")

    def get_skill(self, name: str) -> Optional[Dict]:
        """
        读取 skill 配置

        Args:
            name: skill 名称

        Returns:
            skill 配置字典，不存在则返回 None
        """
        skill_dir = self.registry_dir / name
        skill_path = skill_dir / "SKILL.md"

        if not skill_path.exists():
            return None

        content = skill_path.read_text(encoding='utf-8')
        parsed = self._parse_skill_md(content)

        return {
            "name": name,
            "frontmatter": parsed["frontmatter"],
            "instructions": parsed["instructions"],
            "path": str(skill_path),
            "support_files": self._get_support_files(skill_dir)
        }

    def _get_support_files(self, skill_dir: Path) -> List[str]:
        """获取 skill 的支持文件列表"""
        files = []
        for file in skill_dir.iterdir():
            if file.is_file() and file.name != "SKILL.md":
                files.append(str(file))
        return files

    def list_skills(self) -> List[Dict]:
        """
        列出所有可用 skills

        Returns:
            skill 信息列表
        """
        skills = []
        for skill_dir in self.registry_dir.iterdir():
            if skill_dir.is_dir():
                name = skill_dir.name
                skill_info = self.get_skill(name)
                if skill_info:
                    skills.append({
                        "name": name,
                        "description": skill_info["frontmatter"].get("description", ""),
                        "allowed-tools": skill_info["frontmatter"].get("allowed-tools", []),
                        "context": skill_info["frontmatter"].get("context"),
                        "agent": skill_info["frontmatter"].get("agent")
                    })
        return skills

    def delete_skill(self, name: str) -> bool:
        """
        删除 skill 目录

        Args:
            name: skill 名称

        Returns:
            是否成功删除
        """
        skill_dir = self.registry_dir / name
        if not skill_dir.exists():
            return False

        shutil.rmtree(skill_dir)

        # 更新配置
        if "skills" in self.config and name in self.config["skills"]:
            del self.config["skills"][name]
            self._save_config()

        logger.info(f"Deleted skill: {name}")
        return True

    def reload_from_config(self) -> None:
        """从配置文件重新加载所有 skills"""
        if "skills" not in self.config:
            return

        for name, config in self.config["skills"].items():
            self.register_skill(name, config)

        logger.info(f"Reloaded {len(self.config['skills'])} skills from config")

    def update_skill(self, name: str, config: Dict) -> bool:
        """
        更新 skill 配置

        Args:
            name: skill 名称
            config: 新的配置

        Returns:
            是否成功更新
        """
        if name not in [s["name"] for s in self.list_skills()]:
            return False

        self.register_skill(name, config)
        logger.info(f"Updated skill: {name}")
        return True
