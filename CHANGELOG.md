# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/) as
expressed through [PEP 440](https://peps.python.org/pep-0440/) version
identifiers.

## [Unreleased]

### Added

- `REDMINE_SSL_VERIFY` environment variable to control TLS certificate
  verification for outbound calls to Redmine. Defaults to `true`; set to
  `false` only for a trusted self-signed/internal certificate you cannot
  otherwise validate — see [SECURITY.md](SECURITY.md#network-exposure).

## [1.0.2] - 2026-08-17

### Fixed

- `log_time` now resolves `project_identifier` to a numeric ID before
  calling the Redmine API. `POST /time_entries.json` only accepts a numeric
  `project_id`, unlike `POST /issues.json` which also accepts the string
  identifier — passing a slug (e.g. `mcp-test`) previously failed with
  `Error: Project is invalid`, even though every `project_identifier`
  parameter's docstring promises it accepts either form. (#15)

## [1.0.1] - 2026-08-16

The `v1.0.0` package was published to PyPI from a commit that predated the
repository's rename from `alsimoes/mcp-redmine` to
`alsimoes/mcp-redmine-rest`, so its PyPI project metadata is stuck pointing
at the old (redirecting) URLs. This release carries no code changes, only
metadata fixes, so those URLs are correct going forward.

### Changed

- `pyproject.toml`'s `[project.urls]` (Homepage, Repository, Issues,
  Changelog) now point at `alsimoes/mcp-redmine-rest` instead of the
  renamed-away `alsimoes/mcp-redmine`.
- The package description (`pyproject.toml` and the `mcp_redmine` module
  docstring) no longer implies this server is Claude-only — it now reads
  "connects Claude, or any other MCP client, to a Redmine instance", matching
  the README and the GitHub repository description.

## [1.0.0] - 2026-08-09

First stable release, prepared for submission to the Cline MCP Marketplace.

### Changed

- **The distribution is now named `mcp-redmine-rest`, and the console script it
  installs is `mcp-redmine-rest`** (both were `mcp-redmine`). This is a
  breaking change: `pip install mcp-redmine` and `uv tool install mcp-redmine`
  no longer install this server, and any MCP client configured with
  `"command": "mcp-redmine"` must be updated.

  The reason is a name collision: `mcp-redmine` on PyPI is
  [an unrelated project](https://github.com/runekaagaard/mcp-redmine) by a
  different author, so the old instructions installed someone else's server —
  and the two console scripts shadowed each other when both were installed.

  The import name is unchanged: `python -m mcp_redmine` works exactly as
  before, so configurations that invoke the module rather than the console
  script need no edit.
- Development status is now `5 - Production/Stable` (was `4 - Beta`).
- `.mcp.json` (Claude Code's per-workspace config) is no longer tracked in
  git, even in its sanitized form — copy the new `.mcp.json.example` and fill
  in your own `REDMINE_URL`/`REDMINE_API_KEY` to get a working local file.

### Added

- `llms-install.md`, an imperative installation guide for agent-driven
  setup (prerequisites, the correct install command, required environment
  variables, and a post-install verification call), and a **Cline** section
  in the README alongside Claude Desktop/Code, with the
  `cline_mcp_settings.json` block.
- Project logo (`docs/mcp_redmine_logo.png`, 400×400 PNG), required for the
  Cline MCP Marketplace submission.

### Security

- **File uploads are now allowlist-only and disabled by default.**
  `attach_file_to_issue`, `attach_file_to_wiki_page`, and
  `upload_project_file` refuse every `file_path` unless
  `REDMINE_UPLOAD_ROOTS` is configured with the directories the server may
  read from. It's an environment variable, deliberately not a tool
  parameter or a confirmation flag: those are things a model produces, and
  prompt injection — an issue comment or wiki page instructing the agent to
  attach a local file like `~/.ssh/id_rsa` — means the model isn't
  trustworthy input for that decision. An operator-set environment
  variable is outside the conversation's reach.

  Paths are resolved (following symlinks, collapsing `..`) and checked
  against the allowlist **before** the server even looks at whether the
  file exists, so a path outside the allowlist can't be used to probe the
  server's filesystem for what's there. A defense-in-depth denylist also
  refuses common credential-file patterns (`.env*`, SSH private keys,
  `.netrc`, `.aws/credentials`, `.kube/config`, and similar) even inside an
  allowed directory — a heuristic, not the actual security boundary. See
  [SECURITY.md](SECURITY.md#file-uploads-prompt-injection-is-the-default-threat-model).

  This is a breaking change for the three upload tools' previous
  no-configuration-required behavior, but it lands inside 1.0.0 rather than
  as a 2.0.0: the package has never been published, so nobody's setup
  breaks.

### Fixed

- Removed the redundant `server.py` and `run_server.py` launchers at the
  repository root; they duplicated `python -m mcp_redmine` and broke `ruff`
  (`I001`/`E402`), which was turning CI red on `main`.
- `CLINE_SETUP.md` is now in English (was Portuguese) and no longer hardcodes
  the maintainer's local `C:/dev/repos/mcp-redmine` path.
- The versioned `.mcp.json` example no longer leaks the maintainer's internal
  Redmine hostname or uses `${REDMINE_API_KEY}` shell-expansion syntax that
  Cline does not expand.

### Removed

- Internal working notes not relevant to a public repository:
  `MCP_SETUP_FIXES.md` (personal debugging log), `COWORK_SETUP.md`
  (instructions for an internal tool), and `docs/mcp-redmine-costs.xlsx`
  (the maintainer's LLM cost spreadsheet) are no longer tracked in git.

## [0.1.0] - 2026-07-31

First public release. This version reworks the project from a private,
Portuguese-language script into a packaged, English-language, tested project
suitable for public use.

### Changed

- **Every public identifier is now in English**: tool names, parameters, and
  JSON response keys. This is a breaking change for anyone who configured an
  MCP client against the earlier, private version of this server. The
  renaming follows a consistent pattern:

  | Old prefix (Portuguese) | New prefix (English) |
  |---|---|
  | `listar_*` | `list_*` |
  | `detalhar_*` | `get_*` |
  | `criar_*` | `create_*` |
  | `atualizar_*` | `update_*` |
  | `excluir_*` | `delete_*` |
  | `anexar_*` | `attach_*` / `upload_*` |
  | `buscar` | `search` |

  Parameters that map directly to a Redmine API field now use Redmine's own
  field name (e.g. `responsavel_id` → `assigned_to_id`). The full mapping is
  in the project's git history; the current names are documented in
  [docs/TOOLS.md](docs/TOOLS.md).
- Restructured the single-file `server.py` into an installable package
  (`src/mcp_redmine/`) with one module per Redmine resource under
  `tools/`.
- Centralized error handling into a `@tool` decorator, replacing the
  try/except-and-format block that used to be repeated in nearly every tool.
  A bug in a tool now propagates instead of being silently swallowed
  alongside expected Redmine failures.
- Replaced the fixed `ensure_ascii=False` JSON output with plain
  `json.dumps(..., indent=2)`, since responses are ASCII now.

### Fixed

- The server used to print a configuration error to stderr but keep running
  with an empty `REDMINE_URL`, so every tool call then failed with a
  confusing network error. It now validates configuration at startup and
  exits immediately with an actionable message.
- Docstrings were reformatted to comply with
  [PEP 257](https://peps.python.org/pep-0257/) (summary line immediately
  after the opening quotes, not after a blank line).

### Added

- Full type hints throughout (`mypy --strict`, [PEP 484](https://peps.python.org/pep-0484/)),
  with a `py.typed` marker ([PEP 561](https://peps.python.org/pep-0561/)).
- Packaging via `pyproject.toml`
  ([PEP 517](https://peps.python.org/pep-0517/),
  [PEP 518](https://peps.python.org/pep-0518/),
  [PEP 621](https://peps.python.org/pep-0621/)), with a `mcp-redmine`
  console script entry point.
- Test suite (`pytest` + `responses`), with no network access required.
- GitHub Actions CI: lint, format check, type check, and tests across Python
  3.10–3.13, plus a build/`twine check` job.
- `LICENSE` (MIT), `SECURITY.md`, `CONTRIBUTING.md`, `.env.example`, and
  `docs/TOOLS.md`.

### Removed

- References to the maintainer's private Redmine hostname and the stray,
  non-functional `setup.ps1`.

[0.1.0]: https://github.com/alsimoes/mcp-redmine-rest/tree/7003b0b

[Unreleased]: https://github.com/alsimoes/mcp-redmine-rest/compare/v1.0.2...HEAD
[1.0.2]: https://github.com/alsimoes/mcp-redmine-rest/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/alsimoes/mcp-redmine-rest/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/alsimoes/mcp-redmine-rest/compare/b1523ed...v1.0.0
