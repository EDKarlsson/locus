# Toolchain

Languages, package managers, and development tool conventions.
Read this room when you need to know how to run, build, or test things.

## Languages & Runtimes

- **Python**: 3.11+, managed via `uv`. Always use `uv run <cmd>` — never bare `python`.
- Add your languages here.

## Package Management

- `uv` for Python: `uv sync`, `uv add <dep>`, `uv run pytest`
- Add your tools here.

## Testing

- `uv run pytest tests/ -v`
- Add your test conventions here.

## Key Commands

| Task | Command |
|---|---|
| Install deps | `uv sync --extra dev` |
| Run tests | `uv run pytest` |
| Add your commands | here |

## References

- [`sessions/`](./sessions/) — recent toolchain changes and discoveries
