"""Unit tests for locus.mcp — MCP server tools (#21, #22)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from locus.mcp.palace import assert_writable, find_palace, safe_resolve
from locus.mcp import server as mcp_server


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def palace(tmp_path: Path) -> Path:
    """A minimal valid palace tree."""
    (tmp_path / "INDEX.md").write_text("# Index\n\n| Room | Path |\n|---|---|\n| networking | global/networking |\n")
    (tmp_path / "global").mkdir()
    (tmp_path / "global" / "networking").mkdir()
    (tmp_path / "global" / "networking" / "networking.md").write_text(
        "# Networking\n\nWireGuard is a fast VPN.\n"
    )
    (tmp_path / "global" / "networking" / "sessions").mkdir()
    (tmp_path / "global" / "networking" / "sessions" / "2026-03-01.md").write_text("## Session\n")
    (tmp_path / "_metrics").mkdir()
    (tmp_path / "_metrics" / "2026-03-01T120000Z.json").write_text(
        json.dumps({"schema_version": "1", "task": "test", "palace_path": str(tmp_path)})
    )
    return tmp_path


@pytest.fixture(autouse=True)
def inject_palace(palace: Path) -> None:
    """Point the module-level server at the test palace."""
    mcp_server._palace_root = palace


# ---------------------------------------------------------------------------
# palace.py — find_palace
# ---------------------------------------------------------------------------

class TestFindPalace:
    def test_explicit_path(self, tmp_path: Path) -> None:
        result = find_palace(str(tmp_path))
        assert result == tmp_path.resolve()

    def test_env_var(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOCUS_PALACE", str(tmp_path))
        result = find_palace()
        assert result == tmp_path.resolve()

    def test_cwd_locus(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        locus_dir = tmp_path / ".locus"
        locus_dir.mkdir()
        monkeypatch.chdir(tmp_path)
        result = find_palace()
        assert result == locus_dir.resolve()

    def test_missing_path_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            find_palace(str(tmp_path / "nonexistent"))

    def test_no_palace_raises(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("LOCUS_PALACE", raising=False)
        # Only raises if ~/.locus also doesn't exist; mock home to tmp.
        monkeypatch.setenv("HOME", str(tmp_path))
        with pytest.raises(ValueError, match="No palace found"):
            find_palace()


# ---------------------------------------------------------------------------
# palace.py — safe_resolve
# ---------------------------------------------------------------------------

class TestSafeResolve:
    def test_valid_relative_path(self, palace: Path) -> None:
        result = safe_resolve(palace, "global/networking/networking.md")
        assert result == palace / "global" / "networking" / "networking.md"

    def test_strips_leading_slash(self, palace: Path) -> None:
        result = safe_resolve(palace, "/global/networking/networking.md")
        assert result == palace / "global" / "networking" / "networking.md"

    def test_traversal_rejected(self, palace: Path) -> None:
        with pytest.raises(ValueError, match="escapes the palace root"):
            safe_resolve(palace, "../../etc/passwd")

    def test_root_itself_ok(self, palace: Path) -> None:
        result = safe_resolve(palace, "")
        assert result == palace


# ---------------------------------------------------------------------------
# palace.py — assert_writable
# ---------------------------------------------------------------------------

class TestAssertWritable:
    def test_metrics_blocked(self, palace: Path) -> None:
        target = palace / "_metrics" / "something.json"
        with pytest.raises(ValueError, match="_metrics"):
            assert_writable(palace, target)

    def test_sessions_blocked(self, palace: Path) -> None:
        target = palace / "global" / "networking" / "sessions" / "2026-03-01.md"
        # sessions/ is nested under a room — still blocked
        with pytest.raises(ValueError, match="sessions"):
            assert_writable(palace, target)

    def test_valid_md_allowed(self, palace: Path) -> None:
        target = palace / "global" / "networking" / "networking.md"
        assert_writable(palace, target)  # should not raise

    def test_binary_extension_blocked(self, palace: Path) -> None:
        target = palace / "global" / "networking" / "data.bin"
        with pytest.raises(ValueError, match="Extension"):
            assert_writable(palace, target)

    def test_yaml_allowed(self, palace: Path) -> None:
        target = palace / "global" / "config.yaml"
        assert_writable(palace, target)  # should not raise


# ---------------------------------------------------------------------------
# memory_list
# ---------------------------------------------------------------------------

class TestMemoryList:
    def test_no_path_returns_index(self) -> None:
        result = mcp_server.memory_list()
        assert "Index" in result
        assert "networking" in result

    def test_empty_string_returns_index(self) -> None:
        result = mcp_server.memory_list("")
        assert "Index" in result

    def test_room_path_lists_files(self) -> None:
        result = mcp_server.memory_list("global/networking")
        assert "networking.md" in result

    def test_missing_path_returns_message(self) -> None:
        result = mcp_server.memory_list("does/not/exist")
        assert "not found" in result.lower()

    def test_file_path_returns_contents(self) -> None:
        result = mcp_server.memory_list("global/networking/networking.md")
        assert "WireGuard" in result

    def test_traversal_raises(self) -> None:
        with pytest.raises(ValueError, match="escapes"):
            mcp_server.memory_list("../../etc")


# ---------------------------------------------------------------------------
# memory_read
# ---------------------------------------------------------------------------

class TestMemoryRead:
    def test_reads_existing_file(self) -> None:
        result = mcp_server.memory_read("global/networking/networking.md")
        assert "WireGuard" in result

    def test_missing_file_returns_message(self) -> None:
        result = mcp_server.memory_read("does/not/exist.md")
        assert "not found" in result.lower()

    def test_directory_returns_hint(self) -> None:
        result = mcp_server.memory_read("global/networking")
        assert "directory" in result.lower()

    def test_reads_index(self) -> None:
        result = mcp_server.memory_read("INDEX.md")
        assert "Index" in result

    def test_traversal_raises(self) -> None:
        with pytest.raises(ValueError, match="escapes"):
            mcp_server.memory_read("../../etc/passwd")


# ---------------------------------------------------------------------------
# memory_write
# ---------------------------------------------------------------------------

class TestMemoryWrite:
    def test_writes_new_file(self, palace: Path) -> None:
        result = mcp_server.memory_write("global/networking/notes.md", "# Notes\n\nHello.\n")
        assert "Written" in result
        written = (palace / "global" / "networking" / "notes.md").read_text()
        assert "Hello." in written

    def test_creates_parent_dirs(self, palace: Path) -> None:
        mcp_server.memory_write("global/new-room/new-room.md", "# New Room\n")
        assert (palace / "global" / "new-room" / "new-room.md").exists()

    def test_overwrites_existing(self, palace: Path) -> None:
        mcp_server.memory_write("global/networking/networking.md", "# Updated\n")
        content = (palace / "global" / "networking" / "networking.md").read_text()
        assert "Updated" in content
        assert "WireGuard" not in content

    def test_metrics_blocked(self) -> None:
        with pytest.raises(ValueError, match="_metrics"):
            mcp_server.memory_write("_metrics/foo.json", "{}")

    def test_binary_extension_blocked(self) -> None:
        with pytest.raises(ValueError, match="Extension"):
            mcp_server.memory_write("global/data.exe", "bad")

    def test_traversal_blocked(self) -> None:
        with pytest.raises(ValueError, match="escapes"):
            mcp_server.memory_write("../../evil.md", "evil")

    def test_line_count_in_result(self) -> None:
        result = mcp_server.memory_write("global/test.md", "line1\nline2\nline3\n")
        assert "3" in result

    def test_sessions_blocked(self) -> None:
        with pytest.raises(ValueError, match="sessions"):
            mcp_server.memory_write(
                "global/networking/sessions/2026-03-02.md", "## Session\n"
            )


# ---------------------------------------------------------------------------
# memory_search
# ---------------------------------------------------------------------------

class TestMemorySearch:
    def test_finds_pattern(self) -> None:
        result = mcp_server.memory_search("WireGuard")
        assert "networking.md" in result
        assert "WireGuard" in result

    def test_no_match_returns_message(self) -> None:
        result = mcp_server.memory_search("xyzzy_not_found")
        assert "No matches" in result

    def test_scoped_to_path(self) -> None:
        result = mcp_server.memory_search("Index", path="global/networking")
        # INDEX.md is at root, not inside networking/ — should not appear
        assert "INDEX.md" not in result

    def test_invalid_path_returns_message(self) -> None:
        result = mcp_server.memory_search("anything", path="no/such/path")
        assert "not found" in result.lower()

    def test_traversal_in_path_raises(self) -> None:
        with pytest.raises(ValueError, match="escapes"):
            mcp_server.memory_search("anything", path="../../etc")

    def test_case_insensitive_python_fallback(self, palace: Path) -> None:
        result = mcp_server._search_python("wireguard", palace, palace)
        assert "networking.md" in result

    def test_rg_output_uses_relative_paths(self, palace: Path) -> None:
        # rg JSON formatter should strip the palace root from paths
        result = mcp_server.memory_search("WireGuard")
        assert str(palace) not in result
        assert "networking.md" in result

    def test_python_invalid_regex_returns_error(self, palace: Path) -> None:
        result = mcp_server._search_python("[invalid", palace, palace)
        assert "Invalid search pattern" in result
