.PHONY: install-skills install test lint

# Sync all locus skills from skills/claude/ to ~/.claude/skills/
install-skills:
	@bash scripts/install-skills.sh

install-skills-dry:
	@bash scripts/install-skills.sh --dry-run

# Install the Python package in editable mode
install:
	uv pip install -e .

# Run unit tests
test:
	uv run pytest tests/unit/ -q

# Lint
lint:
	uv run ruff check locus/ tests/
