"""
Structured contracts for registry scanning and execution-facing metadata.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class ExecutionConfig(BaseModel):
    """Normalized execution block for a skill."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["llm", "script"] = "llm"
    handler: Optional[str] = None
    entrypoint: str = "main"
    timeout: int = Field(default=30, ge=1, le=3600)

    @model_validator(mode="after")
    def validate_script_requirements(self) -> "ExecutionConfig":
        if self.type == "script" and not self.handler:
            raise ValueError("script execution requires 'handler'")
        return self


class AgentFrontmatter(BaseModel):
    """Validated agent metadata."""

    model_config = ConfigDict(extra="allow")

    name: str
    description: str = ""
    tools: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    subagents: List[str] = Field(default_factory=list)
    model: str = "inherit"
    max_turns: Optional[int] = Field(default=None, ge=1)


class SkillFrontmatter(BaseModel):
    """Validated skill metadata."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    name: str
    description: str = ""
    allowed_tools: List[str] = Field(default_factory=list, alias="allowed-tools")
    context: Optional[str] = None
    agent: Optional[str] = None


class RegistryError(BaseModel):
    """A registry validation issue discovered during scan."""

    kind: Literal["agent", "skill"]
    name: str
    path: str
    error: str


class RegistryScanReport(BaseModel):
    """Scanner output with both valid specs and invalid entries."""

    skills: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    agents: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    errors: List[RegistryError] = Field(default_factory=list)

    @property
    def is_healthy(self) -> bool:
        return not self.errors


def format_validation_error(exc: ValidationError) -> str:
    """Compress pydantic errors into a readable single string."""

    parts = []
    for item in exc.errors():
        location = ".".join(str(part) for part in item.get("loc", ()))
        message = item.get("msg", "validation error")
        parts.append(f"{location}: {message}" if location else message)
    return "; ".join(parts)
