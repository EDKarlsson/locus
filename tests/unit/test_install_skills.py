"""Tests for scripts/install-skills.sh."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[2]
SCRIPT = REPO_ROOT / "scripts" / "install-skills.sh"
SKILLS_SRC = REPO_ROOT / "skills" / "claude"


@pytest.fixture()
def dst(tmp_path: Path) -> Path:
    return tmp_path / "skills"


def _run_script(dst: Path, extra_args: list[str] | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["CLAUDE_SKILLS_DIR"] = str(dst)
    return subprocess.run(
        ["bash", str(SCRIPT)] + (extra_args or []),
        capture_output=True,
        text=True,
        env=env,
    )


class TestInstallSkills:
    def test_script_exists_and_is_executable(self):
        assert SCRIPT.exists(), "scripts/install-skills.sh not found"

    def test_dry_run_prints_plan(self, dst: Path):
        result = _run_script(dst, ["--dry-run"])
        assert result.returncode == 0
        assert "[dry-run]" in result.stdout
        # Nothing should have been written
        assert not dst.exists() or not any(dst.iterdir())

    def test_dry_run_lists_all_skills(self, dst: Path):
        result = _run_script(dst, ["--dry-run"])
        expected_skills = [d.name for d in SKILLS_SRC.iterdir() if d.is_dir()]
        for skill in expected_skills:
            assert skill in result.stdout, f"skill '{skill}' missing from dry-run output"

    def test_install_copies_all_skills(self, dst: Path):
        result = _run_script(dst)
        assert result.returncode == 0
        expected = {d.name for d in SKILLS_SRC.iterdir() if d.is_dir()}
        installed = {p.name for p in dst.iterdir() if p.is_dir()}
        assert expected == installed

    def test_each_skill_has_skill_md(self, dst: Path):
        _run_script(dst)
        for skill_dir in dst.iterdir():
            skill_md = skill_dir / "SKILL.md"
            assert skill_md.exists(), f"{skill_dir.name}/SKILL.md not found after install"

    def test_idempotent_second_run(self, dst: Path):
        """Running install-skills twice should not error or duplicate files."""
        result1 = _run_script(dst)
        result2 = _run_script(dst)
        assert result1.returncode == 0
        assert result2.returncode == 0
        installed = list(dst.iterdir())
        # No duplicates — count should be the same as number of source skills
        expected_count = len([d for d in SKILLS_SRC.iterdir() if d.is_dir()])
        assert len(installed) == expected_count

    def test_reports_installed_count(self, dst: Path):
        result = _run_script(dst)
        expected_count = len([d for d in SKILLS_SRC.iterdir() if d.is_dir()])
        assert f"{expected_count} skill(s) installed" in result.stdout

    def test_custom_destination_via_env(self, tmp_path: Path):
        custom_dst = tmp_path / "custom_skills_dir"
        result = _run_script(custom_dst)
        assert result.returncode == 0
        assert custom_dst.exists()
        assert any(custom_dst.iterdir())
