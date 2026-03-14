#!/usr/bin/env bash
# install-skills.sh — sync all locus skills from skills/claude/ to ~/.claude/skills/
#
# Usage:
#   ./scripts/install-skills.sh           # install all skills
#   ./scripts/install-skills.sh --dry-run # show what would be copied
#
# Idempotent: safe to run repeatedly. Uses cp -r so destination mirrors source.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_SRC="$REPO_ROOT/skills/claude"
SKILLS_DST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
fi

if [[ ! -d "$SKILLS_SRC" ]]; then
  echo "ERROR: skills source directory not found: $SKILLS_SRC" >&2
  exit 1
fi

installed=0
for skill_dir in "$SKILLS_SRC"/*/; do
  skill_name="$(basename "$skill_dir")"
  dst="$SKILLS_DST/$skill_name"
  if $DRY_RUN; then
    echo "[dry-run] would install: $skill_name → $dst"
  else
    mkdir -p "$SKILLS_DST"
    cp -r "$skill_dir" "$dst"
    echo "installed: $skill_name"
    installed=$((installed + 1))
  fi
done

if ! $DRY_RUN; then
  echo "---"
  echo "$installed skill(s) installed to $SKILLS_DST"
fi
