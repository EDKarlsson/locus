"""Locus agent configuration."""

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


def build_options(palace_path: Path, max_turns: int = 20) -> ClaudeAgentOptions:
    """Build ClaudeAgentOptions for a Locus agent run.

    Note: allowed-tools SKILL.md frontmatter is ignored by the SDK —
    tool access is controlled exclusively here.
    """
    return ClaudeAgentOptions(
        cwd=palace_path,
        setting_sources=["user", "project"],
        allowed_tools=ALLOWED_TOOLS,
        system_prompt=SYSTEM_PROMPT,
        permission_mode="acceptEdits",
        max_turns=max_turns,
    )
