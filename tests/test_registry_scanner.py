import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from src.core.registry_scanner import RegistryScanner


def _make_temp_root() -> Path:
    workspace_tmp = ROOT / "draft" / ".pytest_tmp"
    workspace_tmp.mkdir(parents=True, exist_ok=True)
    temp_root = workspace_tmp / f"case_{uuid.uuid4().hex}"
    temp_root.mkdir(parents=True, exist_ok=True)
    return temp_root


def test_registry_scanner_parses_valid_frontmatter():
    tmp_root = _make_temp_root()
    skills_dir = tmp_root / "skills"
    agents_dir = tmp_root / "agents"
    skill_dir = skills_dir / "demo-skill"
    skill_dir.mkdir(parents=True)
    agents_dir.mkdir(parents=True)

    (skill_dir / "SKILL.md").write_text(
        """---
name: demo-skill
description: Demo
allowed-tools:
  - Read
execution:
  type: script
  handler: scripts/run.py
  entrypoint: main
  timeout: 12
---

Skill body
""",
        encoding="utf-8",
    )

    (agents_dir / "demo-agent.md").write_text(
        """---
name: demo-agent
description: Demo agent
skills:
  - demo-skill
subagents: []
---

Agent body
""",
        encoding="utf-8",
    )

    report = RegistryScanner(skills_dir=skills_dir, agents_dir=agents_dir).scan()

    assert report["errors"] == []
    assert report["skills"]["demo-skill"]["execution"]["handler"] == "scripts/run.py"
    assert report["skills"]["demo-skill"]["frontmatter"]["allowed-tools"] == ["Read"]
    assert report["agents"]["demo-agent"]["frontmatter"]["skills"] == ["demo-skill"]


def test_registry_scanner_reports_invalid_entries():
    tmp_root = _make_temp_root()
    skills_dir = tmp_root / "skills"
    agents_dir = tmp_root / "agents"
    bad_skill_dir = skills_dir / "bad-skill"
    bad_skill_dir.mkdir(parents=True)
    agents_dir.mkdir(parents=True)

    (bad_skill_dir / "SKILL.md").write_text(
        """---
name: bad-skill
execution:
  type: script
---

Broken skill
""",
        encoding="utf-8",
    )

    report = RegistryScanner(skills_dir=skills_dir, agents_dir=agents_dir).scan()

    assert "bad-skill" not in report["skills"]
    assert len(report["errors"]) == 1
    assert report["errors"][0]["kind"] == "skill"
    assert "handler" in report["errors"][0]["error"]
