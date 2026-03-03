# MCP Server

Defines the Locus MCP server: transport, tool surface, safety model, and
configuration. This is a thin file-system adapter over the existing palace
structure — no new concepts, just a standardised interface that any MCP-capable
client (Claude Desktop, Cursor, Zed) can consume without needing the skill files.

---

## Transport

**stdio** — the standard for locally-run MCP servers. The server is launched as
a subprocess; the client communicates over stdin/stdout. No network port is
opened.

HTTP (SSE / Streamable HTTP) is not implemented in v0.5. It can be added later
for multi-client or remote scenarios.

---

## Tool Surface

Four tools cover the full palace lifecycle:

| Tool | Arguments | Returns | Notes |
|---|---|---|---|
| `memory_list` | `path?: str` | Markdown or file listing | Omit `path` → returns `INDEX.md` content. Pass a room path → lists files in that room. |
| `memory_read` | `path: str` | File contents as string | Reads any file within the palace. Path is relative to the palace root. |
| `memory_write` | `path: str`, `content: str` | Confirmation message | Atomic write. Refuses writes outside palace root or into `_metrics/`. |
| `memory_search` | `query: str`, `path?: str` | Ranked result list | Full-text search across the palace (or a sub-path). Uses ripgrep if available, falls back to Python `re`. |

### Design rationale

- **`memory_list` without a path returns `INDEX.md`** — this mirrors the skill's
  Step 1 (always enter via the index) and gives clients the routing table they
  need to navigate further.
- **Writes are blocked to `_metrics/`** — that directory is owned by the
  `locus-audit` / metrics pipeline. MCP clients should not write metrics files.
- **`memory_search` scope defaults to the full palace** — the optional `path`
  argument narrows the search to a specific room or subdirectory, which is
  useful when the client already knows which room to search.

---

## Safety Model

All path arguments are validated before any file I/O:

1. **Resolve to absolute path** within the palace root.
2. **Reject path traversal** — any resolved path that does not start with the
   palace root prefix raises an error.
3. **Reject writes to system directories** — `_metrics/`, `sessions/`, and
   `archived/` are read-only via MCP. These directories are managed by the
   pipeline, not by external clients.
4. **Reject writes to binary files** — only `.md`, `.txt`, `.json`, `.yaml`,
   and `.yml` extensions are permitted for writes.

---

## Configuration

The palace root is supplied at server startup:

```
locus-mcp --palace /path/to/palace
```

Or via environment variable:

```
LOCUS_PALACE=/path/to/palace locus-mcp
```

If neither is provided, the server looks for a `.locus/` directory in the
current working directory, then falls back to `~/.locus/`.

---

## Implementation

- **Package**: `locus/mcp/`
- **Server**: `locus/mcp/server.py` — `FastMCP` instance, all four tools
- **Entry point**: `locus/mcp/main.py` — CLI wrapper (`locus-mcp`)
- **Framework**: `mcp.server.fastmcp.FastMCP` (stdio transport)
- **Search backend**: `subprocess` call to `rg` (ripgrep); Python `re` fallback

---

## MCP Client Configuration Examples

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "locus": {
      "command": "uvx",
      "args": ["locus-agent", "locus-mcp", "--palace", "/path/to/palace"]
    }
  }
}
```

### Cursor / Zed (`.cursor/mcp.json` or `.zed/settings.json`)

```json
{
  "mcp": {
    "servers": {
      "locus": {
        "command": "locus-mcp",
        "args": ["--palace", "/path/to/palace"]
      }
    }
  }
}
```

---

## Relationship to v1 Skills

The MCP server and the skill files (`skills/claude/locus/`) are complementary,
not mutually exclusive:

| Capability | Skill | MCP |
|---|---|---|
| Navigate palace | Step 1–2 (read INDEX, follow rooms) | `memory_list` + `memory_read` |
| Write canonical facts | Step 3 | `memory_write` |
| Write session logs | Step 4 | `memory_write` (append) |
| Full-text search | Not available | `memory_search` |
| Works without tool approval | No (Bash/Read/Write required) | Yes (single MCP permission) |

The MCP layer is the recommended interface for MCP-capable clients. The skills
remain the interface for Claude Code, which does not use MCP for local tools.
