# CLAUDE.md

## What this is

An MCP server that exposes the Redmine REST API as tools for Claude (or any
MCP client), over stdio. Thin proxy — it forwards calls to Redmine and turns
failures into readable text; it does not implement its own authorization.

## Layout (src-layout)

- `src/mcp_redmine/app.py` — FastMCP instance, the `tool` decorator, `main()`
  entry point.
- `src/mcp_redmine/config.py` — reads `REDMINE_URL` / `REDMINE_API_KEY` /
  `REDMINE_TIMEOUT` / `REDMINE_UPLOAD_ROOTS` / `REDMINE_SSL_VERIFY` from the
  environment.
- `src/mcp_redmine/client.py` — HTTP client wrapping the Redmine REST API.
- `src/mcp_redmine/errors.py` — `RedmineError` and message formatting.
- `src/mcp_redmine/tools/*.py` — one module per Redmine resource (issues,
  projects, users, wiki, ...). `tools/__init__.py` imports every submodule so
  their `@tool`-decorated functions register with FastMCP as a side effect —
  nothing else should import from `tools/__init__.py` directly.
- `tests/` — pytest, using `responses` to mock the Redmine HTTP API.

## Tool registration pattern

Every tool function is decorated with `@tool` from `app.py`. That decorator:

- Registers the function with the shared `mcp` FastMCP instance.
- Catches `RedmineError` and returns `f"Error: {redmine_error_message(exc)}"`
  as a normal string return value instead of letting it propagate. Tools that
  need custom partial-failure handling (e.g. an upload that succeeds but a
  follow-up link fails) catch `RedmineError` themselves before this wrapper
  sees it.
- Any non-`RedmineError` exception is a bug and is left to propagate.

New tools go in the relevant `tools/<resource>.py` module (or a new one,
added to the import list in `tools/__init__.py`).

## Deliberately missing tools

There is no `delete_project` or `delete_user` tool, on purpose — see
[SECURITY.md](SECURITY.md#deliberate-omissions). Both operations are
irreversible; use `archive_project` and `update_user(status=3)` instead. Do
not add delete tools for these two resources.

## Running checks (local venv)

The virtualenv lives in `.venv/`. These only read; they never modify the
working tree:

```
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m mypy src
```

To actually reformat (this rewrites files, so it is not a check):

```
.venv/bin/python -m ruff format .
```

On Windows the interpreter is at `.venv/Scripts/python.exe` instead. Use
forward slashes there too — under Git Bash `\` is an escape character, so
`.venv\Scripts\python.exe` fails with "command not found".

- Ruff lints with `E`, `W`, `F`, `I`, `N`, `D`, `UP`, `B`, `ANN`, `S`, and
  `RUF` enabled — see `[tool.ruff.lint]` in `pyproject.toml` for the
  authoritative list and the ignores. The ones that bite most often: `D`
  (pydocstyle, Google convention) and `ANN` (type annotations) mean new code
  needs full docstrings and type hints, and `S` applies bandit-style security
  checks. `tests/**` is exempt from `S`, `ANN`, `D`.
- Mypy runs in `strict` mode against `src`.

## Configuration

`REDMINE_URL` and `REDMINE_API_KEY` are required. The rest are optional:
`REDMINE_TIMEOUT` (default 15s), `REDMINE_UPLOAD_ROOTS` (unset means uploads
are refused — see [SECURITY.md](SECURITY.md#file-uploads-prompt-injection-is-the-default-threat-model)),
and `REDMINE_SSL_VERIFY` (default true; only set it false for a trusted
self-signed cert — see [SECURITY.md](SECURITY.md#network-exposure)). Never
commit real values — use your MCP client's env config or a local, gitignored
`.env`.

`load_settings()` merges a `.env` into the environment first, without
overriding variables that are already set, so the client's `env` block wins.
The file is looked up at the repository root, or at `REDMINE_ENV_FILE` if
that is set. `tests/conftest.py` has an autouse fixture pointing
`REDMINE_ENV_FILE` at a nonexistent path so a developer's real `.env` cannot
leak into the tests.

Claude Desktop builds a minimal environment for the servers it launches and
does not pass through user or shell variables. Exporting a variable from your
shell rc (or `setx` on Windows) has no effect there — put it in the server's
`env` block instead.
