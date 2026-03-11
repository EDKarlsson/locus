"""Locus agent configuration."""

from __future__ import annotations

from pathlib import Path
from claude_agent_sdk import ClaudeAgentOptions

ALLOWED_TOOLS = ["Skill", "Read", "Write", "Bash", "Glob", "Grep"]

# System prompt is minimal — SKILL.md provides navigation instructions.
# This only establishes the agent's role and the one hard rule.
SYSTEM_PROMPT = """\
You are a Locus memory agent. Locus is a hierarchical markdown-based memory
system where directories are rooms and files are knowledge.

When given a task:
1. Start by reading INDEX.md in the palace root to discover available rooms.
2. Navigate to only the rooms relevant to your task — do not load the full palace.
3. Write using the correct mode: append-only session logs for ephemeral findings,
   explicit edits for canonical facts.
4. Report which files you read and their line counts at the end of every task.

Never load files speculatively. Minimal context is the goal.
"""


def build_options(
    palace_path: Path,
    max_turns: int = 20,
    security_ctx: "SecurityContext | None" = None,
) -> ClaudeAgentOptions:
    """Build ClaudeAgentOptions for a Locus agent run.

    Note: allowed-tools SKILL.md frontmatter is ignored by the SDK —
    tool access is controlled exclusively here.

    If security_ctx is provided, security hooks are registered and the
    system prompt is extended with a signed SECURITY CONTEXT block.
    """
    system_prompt = SYSTEM_PROMPT

    if security_ctx is not None:
        from locus.security.nonce import inject_security_context
        from locus.mcp.palace import _slug_from_path
        palace_slug = _slug_from_path(palace_path.resolve())
        system_prompt = inject_security_context(
            SYSTEM_PROMPT,
            nonce=security_ctx.session_nonce,
            keypair=security_ctx.keystore.active,
            palace_slug=palace_slug,
        )

    return ClaudeAgentOptions(
        cwd=palace_path,
        setting_sources=["user", "project"],
        allowed_tools=ALLOWED_TOOLS,
        system_prompt=system_prompt,
        permission_mode="acceptEdits",
        max_turns=max_turns,
    )


# Avoid circular import at module level — type hint only
try:
    from locus.security.middleware import SecurityContext
except ImportError:
    SecurityContext = None  # type: ignore[assignment,misc]
