"""
Registry scanner with frontmatter validation and scan reporting.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from core.specs import (
    AgentFrontmatter,
    ExecutionConfig,
    RegistryError,
    RegistryScanReport,
    SkillFrontmatter,
    format_validation_error,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class RegistryScanner:
    """Discover and validate skills and agents from the filesystem registry."""

    def __init__(self, skills_dir: Path = None, agents_dir: Path = None):
        from config import get_config

        cfg = get_config()
        self.skills_dir = Path(skills_dir or cfg.registry.skills_dir)
        self.agents_dir = Path(agents_dir or cfg.registry.agents_dir)
        self.skill_specs: Dict[str, Dict[str, Any]] = {}
        self.agent_specs: Dict[str, Dict[str, Any]] = {}
        self.scan_errors: List[Dict[str, str]] = []

    def scan(self) -> Dict[str, Any]:
        """Scan the registry and cache the result."""

        report = RegistryScanReport()
        report.skills = self._scan_skills(report.errors)
        report.agents = self._scan_agents(report.errors)

        self.skill_specs = report.skills
        self.agent_specs = report.agents
        self.scan_errors = [item.model_dump() for item in report.errors]

        logger.info(
            "Scanned registry: %s skills, %s agents, %s errors",
            len(report.skills),
            len(report.agents),
            len(report.errors),
        )

        return report.model_dump()

    def get_last_scan_report(self) -> Dict[str, Any]:
        """Return the most recently cached scan report."""

        return {
            "skills": self.skill_specs,
            "agents": self.agent_specs,
            "errors": list(self.scan_errors),
        }

    def _scan_skills(self, errors: List[RegistryError]) -> Dict[str, Dict[str, Any]]:
        specs: Dict[str, Dict[str, Any]] = {}
        if not self.skills_dir.exists():
            logger.warning("Skills directory not found: %s", self.skills_dir)
            return specs

        for skill_dir in sorted(self.skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue

            skill_name = skill_dir.name
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue

            spec = self._parse_skill_md(skill_md, skill_name, skill_dir, errors)
            if spec:
                specs[skill_name] = spec

        return specs

    def _scan_agents(self, errors: List[RegistryError]) -> Dict[str, Dict[str, Any]]:
        specs: Dict[str, Dict[str, Any]] = {}
        if not self.agents_dir.exists():
            logger.warning("Agents directory not found: %s", self.agents_dir)
            return specs

        for agent_file in sorted(self.agents_dir.glob("*.md")):
            agent_name = agent_file.stem
            spec = self._parse_agent_md(agent_file, agent_name, errors)
            if spec:
                specs[agent_name] = spec

        return specs

    def _parse_skill_md(
        self,
        md_path: Path,
        skill_name: str,
        skill_dir: Path,
        errors: List[RegistryError],
    ) -> Optional[Dict[str, Any]]:
        try:
            content = md_path.read_text(encoding="utf-8")
            frontmatter, instructions = self._split_frontmatter(content)
            frontmatter["name"] = frontmatter.get("name", skill_name)

            execution_raw = frontmatter.pop("execution", None)
            skill_meta = SkillFrontmatter.model_validate(frontmatter)
            execution = (
                ExecutionConfig.model_validate(execution_raw).model_dump(by_alias=True)
                if execution_raw
                else {}
            )

            spec = {
                "frontmatter": skill_meta.model_dump(by_alias=True),
                "instructions": instructions,
                "base_dir": str(skill_dir),
            }
            if execution:
                spec["execution"] = execution
            return spec
        except Exception as exc:
            self._append_error(errors, "skill", skill_name, md_path, exc)
            return None

    def _parse_agent_md(
        self,
        md_path: Path,
        agent_name: str,
        errors: List[RegistryError],
    ) -> Optional[Dict[str, Any]]:
        try:
            content = md_path.read_text(encoding="utf-8")
            frontmatter, instructions = self._split_frontmatter(content)
            frontmatter["name"] = frontmatter.get("name", agent_name)

            agent_meta = AgentFrontmatter.model_validate(frontmatter)
            return {
                "frontmatter": agent_meta.model_dump(),
                "instructions": instructions,
                "prompt": instructions,
                "base_dir": str(md_path.parent),
                "path": str(md_path),
            }
        except Exception as exc:
            self._append_error(errors, "agent", agent_name, md_path, exc)
            return None

    def _split_frontmatter(self, content: str) -> Tuple[Dict[str, Any], str]:
        lines = content.splitlines()
        if not lines or lines[0].strip() != "---":
            return {}, content.strip()

        end_index = None
        for idx in range(1, len(lines)):
            if lines[idx].strip() == "---":
                end_index = idx
                break

        if end_index is None:
            raise ValueError("unclosed frontmatter block")

        frontmatter_text = "\n".join(lines[1:end_index])
        body = "\n".join(lines[end_index + 1 :]).strip()
        parsed = yaml.safe_load(frontmatter_text) or {}
        if not isinstance(parsed, dict):
            raise ValueError("frontmatter must be a mapping")
        return parsed, body

    def _append_error(
        self,
        errors: List[RegistryError],
        kind: str,
        name: str,
        path: Path,
        exc: Exception,
    ) -> None:
        if hasattr(exc, "errors"):
            message = format_validation_error(exc)  # pydantic ValidationError
        else:
            message = str(exc)

        logger.error("Invalid %s spec '%s' at %s: %s", kind, name, path, message)
        errors.append(
            RegistryError(
                kind=kind,
                name=name,
                path=str(path),
                error=message,
            )
        )

    def get_skill_spec(self, skill_name: str) -> Optional[Dict[str, Any]]:
        return self.skill_specs.get(skill_name)

    def get_agent_spec(self, agent_name: str) -> Optional[Dict[str, Any]]:
        return self.agent_specs.get(agent_name)

    def list_skills(self) -> List[str]:
        return list(self.skill_specs.keys())

    def list_agents(self) -> List[str]:
        return list(self.agent_specs.keys())

    def get_skill_execution_config(self, skill_name: str) -> Optional[Dict[str, Any]]:
        spec = self.skill_specs.get(skill_name)
        if not spec:
            return None
        return spec.get("execution", {})

    def has_script_execution(self, skill_name: str) -> bool:
        execution = self.get_skill_execution_config(skill_name)
        return bool(execution and execution.get("type") == "script")


_scanner: Optional[RegistryScanner] = None


def get_scanner() -> RegistryScanner:
    global _scanner
    if _scanner is None:
        _scanner = RegistryScanner()
    return _scanner
