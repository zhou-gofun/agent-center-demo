"""
注册表扫描器

动态扫描并发现 skills 和 agents，无需 __init__.py 依赖
"""
import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from utils.logger import get_logger

logger = get_logger(__name__)


class RegistryScanner:
    """
    注册表扫描器

    功能：
    1. 扫描 skills/ 和 agents/ 目录
    2. 解析 SKILL.md 和 AGENT.md 文件
    3. 提取执行配置（execution frontmatter）
    4. 返回完整的 specs
    """

    def __init__(self, skills_dir: Path = None, agents_dir: Path = None):
        """
        初始化扫描器

        Args:
            skills_dir: skills 目录路径
            agents_dir: agents 目录路径
        """
        from config import get_config
        cfg = get_config()

        self.skills_dir = Path(skills_dir or cfg.registry.skills_dir)
        self.agents_dir = Path(agents_dir or cfg.registry.agents_dir)

        self.skill_specs: Dict[str, Dict] = {}
        self.agent_specs: Dict[str, Dict] = {}

    def scan(self) -> Dict[str, Dict]:
        """
        扫描所有目录并返回 specs

        Returns:
            {"skills": {name: spec}, "agents": {name: spec}}
        """
        self.skill_specs = self._scan_skills()
        self.agent_specs = self._scan_agents()

        logger.info(f"Scanned {len(self.skill_specs)} skills from {self.skills_dir}")
        logger.info(f"Scanned {len(self.agent_specs)} agents from {self.agents_dir}")

        return {
            "skills": self.skill_specs,
            "agents": self.agent_specs
        }

    def _scan_skills(self) -> Dict[str, Dict]:
        """扫描 skills 目录"""
        specs = {}

        if not self.skills_dir.exists():
            logger.warning(f"Skills directory not found: {self.skills_dir}")
            return specs

        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_name = skill_dir.name
            skill_md = skill_dir / "SKILL.md"

            if not skill_md.exists():
                logger.debug(f"No SKILL.md found for {skill_name}")
                continue

            spec = self._parse_skill_md(skill_md, skill_dir)
            if spec:
                specs[skill_name] = spec

        return specs

    def _scan_agents(self) -> Dict[str, Dict]:
        """扫描 agents 目录"""
        specs = {}

        if not self.agents_dir.exists():
            logger.warning(f"Agents directory not found: {self.agents_dir}")
            return specs

        # Agents are .md files
        for agent_file in self.agents_dir.glob("*.md"):
            agent_name = agent_file.stem
            spec = self._parse_agent_md(agent_file)

            if spec:
                specs[agent_name] = spec

        return specs

    def _parse_skill_md(self, md_path: Path, skill_dir: Path) -> Optional[Dict]:
        """
        解析 SKILL.md 文件

        提取 frontmatter 和 execution 配置
        """
        try:
            content = md_path.read_text(encoding='utf-8')
            return self._parse_markdown_frontmatter(content, skill_dir)
        except Exception as e:
            logger.error(f"Error parsing {md_path}: {e}")
            return None

    def _parse_agent_md(self, md_path: Path) -> Optional[Dict]:
        """解析 AGENT.md 文件"""
        try:
            content = md_path.read_text(encoding='utf-8')
            return self._parse_markdown_frontmatter(content, md_path.parent)
        except Exception as e:
            logger.error(f"Error parsing {md_path}: {e}")
            return None

    def _parse_markdown_frontmatter(self, content: str, base_dir: Path) -> Optional[Dict]:
        """
        解析 Markdown frontmatter

        支持格式：
        ---
        name: skill-name
        description: ...
        execution:
          type: script
          handler: scripts/main.py
        ---
        """
        lines = content.split('\n')
        frontmatter = {}
        instructions = []
        execution = {}

        # 解析 frontmatter
        if lines and lines[0].strip() == "---":
            i = 1
            while i < len(lines) and lines[i].strip() != "---":
                line = lines[i].rstrip()
                i += 1

                if ':' not in line:
                    continue

                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()

                # 处理嵌套的 execution 配置
                if key == "execution":
                    # 继续读取 execution 配置
                    i = self._parse_execution_config(lines, i, execution)
                    continue

                # 处理列表格式
                if value.startswith('[') and value.endswith(']'):
                    value = [v.strip() for v in value[1:-1].split(',') if v.strip()]
                # 处理布尔值
                elif value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False

                frontmatter[key] = value

            # 跳过结束的 ---
            if i < len(lines) and lines[i].strip() == "---":
                i += 1

            # 提取 instructions
            instructions = '\n'.join(lines[i:]).strip()

        # 构建返回的 spec
        spec = {
            "frontmatter": frontmatter,
            "instructions": instructions,
            "base_dir": str(base_dir)
        }

        # 添加 execution 配置
        if execution:
            spec["execution"] = execution

        return spec

    def _parse_execution_config(self, lines: List[str], start_idx: int, execution: Dict) -> int:
        """
        解析 execution 配置块

        支持格式：
        execution:
          type: script
          handler: scripts/main.py
          entrypoint: main
          timeout: 30
        """
        i = start_idx
        current_key = None

        while i < len(lines):
            line = lines[i].rstrip()

            # 检查是否结束
            if line.strip() == "---":
                break

            # 检查缩进（子属性）
            if line.startswith('    ') or line.startswith('\t'):
                # 子属性
                if current_key:
                    value = line.strip()
                    if ':' in value:
                        sub_key, sub_value = value.split(':', 1)
                        sub_key = sub_key.strip()
                        sub_value = sub_value.strip()

                        # 类型转换
                        if sub_key == "timeout":
                            sub_value = int(sub_value)
                        elif sub_value.lower() == 'true':
                            sub_value = True
                        elif sub_value.lower() == 'false':
                            sub_value = False

                        execution[sub_key] = sub_value
            else:
                # 顶层属性
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()

                    if value:
                        if key == "timeout":
                            value = int(value)
                        elif value.lower() == 'true':
                            value = True
                        elif value.lower() == 'false':
                            value = False
                        execution[key] = value

                    current_key = key

            i += 1

        return i

    def get_skill_spec(self, skill_name: str) -> Optional[Dict]:
        """获取 skill spec"""
        return self.skill_specs.get(skill_name)

    def get_agent_spec(self, agent_name: str) -> Optional[Dict]:
        """获取 agent spec"""
        return self.agent_specs.get(agent_name)

    def list_skills(self) -> List[str]:
        """列出所有 skill 名称"""
        return list(self.skill_specs.keys())

    def list_agents(self) -> List[str]:
        """列出所有 agent 名称"""
        return list(self.agent_specs.keys())

    def get_skill_execution_config(self, skill_name: str) -> Optional[Dict]:
        """
        获取 skill 的执行配置

        Returns:
            {"type": "script", "handler": "scripts/main.py", "entrypoint": "main", "timeout": 30}
        """
        spec = self.skill_specs.get(skill_name)
        if not spec:
            return None

        return spec.get("execution", {})

    def has_script_execution(self, skill_name: str) -> bool:
        """检查 skill 是否有脚本执行配置"""
        exec_config = self.get_skill_execution_config(skill_name)
        return exec_config.get("type") == "script" if exec_config else False


# 全局实例
_scanner = None


def get_scanner() -> RegistryScanner:
    """获取扫描器实例"""
    global _scanner
    if _scanner is None:
        _scanner = RegistryScanner()
    return _scanner
