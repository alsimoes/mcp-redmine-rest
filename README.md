# mcp-redmine

[![CI](https://github.com/alsimoes/mcp-redmine-rest/actions/workflows/ci.yml/badge.svg)](https://github.com/alsimoes/mcp-redmine-rest/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)

A [Model Context Protocol](https://modelcontextprotocol.io) server that connects
Claude (Desktop or Code) — or any other MCP client — to a [Redmine](https://www.redmine.org/)
instance through its REST API.

It exposes 73 tools covering, in practice, the entire stable Redmine REST API:
issues, relations, projects, memberships, versions, categories, users, groups,
roles, wiki, time tracking, attachments, project files, news, and search. Point
your agent at a Redmine project and let it read and manage issues, log time,
edit wiki pages, and administer users — all through natural conversation.

## Features

- **Full read/write coverage** of issues, including bulk updates, relations,
  watchers, and comments.
- **Project administration**: create/update/archive projects, manage members,
  versions, and categories.
- **User and group administration**, with deliberately no "delete user" or
  "delete project" tool — see [Security](#security).
- **Wiki**, including nested pages and file attachments.
- **Time tracking**, attachments, project files, news, and full-text search.
- **Readable errors**: every failure comes back as a clear sentence pulled
  from Redmine's own validation response, not a raw stack trace.
- **Nothing to run**: a single Python process talking stdio to your MCP
  client — no database, no server to host, no Docker required.

## Prerequisites

- Python 3.10+
- A Redmine instance with the REST API enabled:
  1. In Redmine, go to **Administration → Settings → API** and enable
     "Enable REST web service" (if not already on).
  2. Go to **My account → API access key** and copy the value.

## Installation

The distribution is published as **`mcp-redmine-rest`**, and the command it
installs is `mcp-redmine-rest`. The shorter `mcp-redmine` name on PyPI belongs
to [an unrelated project](https://github.com/runekaagaard/mcp-redmine) — don't
install that one expecting this server.

If you're pointing an AI agent at this repository to do the setup for you,
[llms-install.md](llms-install.md) is written for exactly that.

### With uv (recommended)

```bash
uv tool install mcp-redmine-rest
```

### With pip

```bash
pip install mcp-redmine-rest
```

### From source

```bash
git clone https://github.com/alsimoes/mcp-redmine-rest.git
cd mcp-redmine-rest

python3 -m venv venv && source venv/bin/activate    # Linux/Mac

pip install -e .
```

On Windows, use `py` and PowerShell rather than a Git Bash/WSL shell — creating
or recreating the venv from a Unix-style shell on Windows overwrites
`venv\pyvenv.cfg` with a Unix `home` path, and every subsequent launch of
`venv\Scripts\python.exe` fails with `No Python at '/usr/bin\python.exe'` (or
similar):

```powershell
git clone https://github.com/alsimoes/mcp-redmine-rest.git
cd mcp-redmine-rest

py -3 -m venv venv
.\venv\Scripts\Activate.ps1

pip install -e .
```

## Configuration

The server reads its configuration from environment variables:

| Variable | Required | Description |
|---|---|---|
| `REDMINE_URL` | Yes | Base URL of your Redmine instance (no trailing slash). |
| `REDMINE_API_KEY` | Yes | Your API access key, from My account → API access key. |
| `REDMINE_TIMEOUT` | No | Per-request timeout in seconds. Defaults to 15. |
| `REDMINE_UPLOAD_ROOTS` | No | Directories the file-upload tools may read from, separated by `os.pathsep` (`;` on Windows, `:` on Linux/macOS). **Unset = uploads disabled.** See [Security](#security). |
| `REDMINE_SSL_VERIFY` | No | Verify the Redmine server's TLS certificate. Defaults to `true`. Set to `false` only for a trusted self-signed/internal cert you cannot otherwise validate — this disables protection against man-in-the-middle attacks on that connection. |

### Keeping the key out of the client configuration

Values missing from the environment are read from a `.env` file, so the API
key does not have to sit in plain text in your MCP client's configuration.
Copy `.env.example` to `.env` in the repository root and fill it in — every
variable in the table above is honoured, so the client's `env` block can be
dropped entirely:

```
REDMINE_URL=https://redmine.example.com
REDMINE_API_KEY=your_api_key_here
REDMINE_TIMEOUT=15
```

The file is gitignored. Variables already present in the environment always
win, so an `env` block in your client's configuration still overrides it. To
keep the file somewhere else, set `REDMINE_ENV_FILE` to its full path.

This matters on Claude Desktop in particular: it launches MCP servers with a
minimal environment it builds itself, so variables you export in your shell
or set with `setx` never reach the server. Use the `env` block or a `.env`
file.

### Claude Desktop

Edit (or create) the Claude Desktop configuration file:

- **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "redmine": {
      "command": "mcp-redmine-rest",
      "env": {
        "REDMINE_URL": "https://redmine.example.com",
        "REDMINE_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

If you installed from source instead of via `uv tool install` / `pip
install`, point `command` at the interpreter in your virtual environment and
pass the script as an argument:

```json
{
  "mcpServers": {
    "redmine": {
      "command": "/full/path/to/mcp-redmine/venv/bin/python",
      "args": ["-m", "mcp_redmine"],
      "env": {
        "REDMINE_URL": "https://redmine.example.com",
        "REDMINE_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

On Windows, point `command` at `venv\Scripts\python.exe` (with `\\` escaped
in JSON):

```json
{
  "mcpServers": {
    "redmine": {
      "command": "C:\\full\\path\\to\\mcp-redmine\\venv\\Scripts\\python.exe",
      "args": ["-m", "mcp_redmine"],
      "env": {
        "REDMINE_URL": "https://redmine.example.com",
        "REDMINE_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

Restart Claude Desktop afterwards. The tools icon (🔨) should show the
Redmine tools as available.

### Claude Code

```bash
claude mcp add redmine \
  --env REDMINE_URL=https://redmine.example.com \
  --env REDMINE_API_KEY=your_api_key_here \
  -- mcp-redmine-rest
```

Confirm with:

```bash
claude mcp list
```

### Cline (VS Code)

Open the MCP settings from the palette — `Ctrl+Shift+P` → **Cline: Open MCP
Config File** — or click the gear next to "MCP Servers" in the Cline sidebar
and choose *Configure MCP Servers*. Either one opens
`cline_mcp_settings.json`; add the server there:

```json
{
  "mcpServers": {
    "redmine": {
      "command": "mcp-redmine-rest",
      "env": {
        "REDMINE_URL": "https://redmine.example.com",
        "REDMINE_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

Use the palette command rather than editing the file by hand — it lives deep
in VS Code's global storage
(`.../User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`),
and the path differs per platform.

If `mcp-redmine-rest` is not on the `PATH` that VS Code sees, use the module
form instead — `"command"` pointing at the interpreter that has the package
installed, with `"args": ["-m", "mcp_redmine"]`, exactly like the Claude
Desktop examples above.

Reload the window (`Ctrl+Shift+P` → *Developer: Reload Window*) and the server
should come up as connected under "MCP Servers". A longer walkthrough,
covering the workspace `.mcp.json` and the Add-Server UI, is in
[CLINE_SETUP.md](CLINE_SETUP.md).

### Other MCP clients

Any client that can launch a local process and speak MCP over stdio works the
same way: run `mcp-redmine-rest` (or `python -m mcp_redmine`) with
`REDMINE_URL` and `REDMINE_API_KEY` set in its environment.

## Run locally (optional)

Useful for a quick sanity check before wiring the server into a client:

```bash
cp .env.example .env   # then edit .env with your values
export $(grep -v '^#' .env | xargs)   # or use a tool like direnv
mcp-redmine-rest
```

If there's no connection error, the server is ready — it waits for MCP
messages on stdin/stdout, so seeing nothing happen in the terminal is normal.
Press Ctrl+C to stop it.

## Usage examples

Once configured, just talk to the agent:

- "List the open issues assigned to me in the Website project."
- "Create a bug in Website titled 'Login button unresponsive on mobile',
  priority high."
- "Move issues #101, #104, and #110 to In Progress and assign them to Alice."
- "Log 3.5 hours on issue #204 for today, activity Development."
- "What's on the wiki page 'Deployment' for the Infra project?"
- "Search for 'timeout' across all projects."

## Available tools

73 tools, grouped by resource. The full reference — signatures, parameters,
return shape, and the caveats that matter (like how `precedes` reschedules
issues, or that `list_custom_fields` requires an administrator) — lives in
[docs/TOOLS.md](docs/TOOLS.md).

| Resource | Tools |
|---|---|
| Issues | `list_issues`, `get_issue`, `create_issue`, `update_issue`, `bulk_update_issues`, `delete_issue`, `add_watcher`, `remove_watcher`, `update_journal_note` |
| Issue relations | `list_issue_relations`, `create_issue_relation`, `delete_issue_relation`, `chain_issues` |
| Projects | `list_projects`, `get_project`, `create_project`, `update_project`, `archive_project` |
| Project members | `list_project_members`, `add_project_member`, `update_project_member`, `remove_project_member` |
| Versions | `list_project_versions`, `create_project_version`, `update_version`, `delete_version` |
| Categories | `list_project_categories`, `create_project_category`, `update_project_category`, `delete_project_category` |
| Users | `get_current_user`, `list_users`, `get_user`, `create_user`, `update_user`, `update_my_account` |
| Groups | `list_groups`, `get_group`, `create_group`, `update_group`, `delete_group`, `add_user_to_group`, `remove_user_from_group` |
| Roles | `list_roles`, `get_role` |
| Wiki | `list_wiki_pages`, `get_wiki_page`, `create_or_update_wiki_page`, `attach_file_to_wiki_page`, `delete_wiki_page` |
| Time tracking | `list_time_entries`, `get_time_entry`, `log_time`, `update_time_entry`, `delete_time_entry`, `list_time_entry_activities` |
| Attachments | `attach_file_to_issue`, `get_attachment`, `update_attachment`, `delete_attachment` |
| Project files | `list_project_files`, `upload_project_file` |
| News | `list_news`, `get_news_item`, `create_news`, `update_news`, `delete_news` |
| Search | `search`, `list_saved_queries` |
| Metadata | `list_statuses_and_priorities`, `list_trackers`, `list_custom_fields`, `list_document_categories` |

### API coverage

| Redmine API resource | Status |
|---|---|
| Issues | Complete (list, read, create, update, bulk, delete, watchers) |
| Issue relations | Complete |
| Projects | Complete **minus deletion** |
| Project members | Complete |
| Versions | Complete |
| Issue categories | Complete |
| Users | Complete **minus deletion** |
| Groups | Complete |
| Roles | Complete (the API is read-only) |
| Wiki | Complete, including nesting and attachments |
| Attachments | Complete |
| Project files | Complete |
| News | Complete |
| Time tracking | Complete |
| Search and saved queries | Complete |
| Trackers, statuses, priorities, activities, custom fields | Complete (the API is read-only) |
| Document categories | Complete (the API is read-only) |

**The two omissions are deliberate.** `delete_project` and `delete_user` are
irreversible and take other people's content down with them — issues, time
entries, wiki pages, authorship. `archive_project` and `update_user` with
`status=3` cover the real use case reversibly. Deleting for real remains a web
UI operation, where confirmation is explicit and human. See
[SECURITY.md](SECURITY.md) for the full reasoning.

Trackers, issue statuses, priorities, and roles have no write operations in
the Redmine API — they're configurable only in Administration. That's not a
gap in this server.

Outside the stable REST API, and therefore outside this server's scope:
repositories and changesets, wiki page protection, and instance-wide settings
screens.

## Error messages

Errors are handled centrally: when Redmine rejects a call, the server reads
the response body — that's where the real explanation lives, in the `errors`
field — and returns that sentence. Without a useful body, it falls back to
the HTTP status with a likely reason:

| Status | Message |
|---|---|
| 401 | invalid or missing API key |
| 403 | not allowed to perform this operation, or the module is disabled for this project |
| 404 | not found (check the ID, or this endpoint may not exist in this Redmine version) |
| 409 | conflict — the resource was changed by someone else |
| 422 | Redmine rejected the data during validation |

This applies to every tool, read and write alike.

## Troubleshooting

- **"REDMINE_URL and REDMINE_API_KEY must be set"**: the server checks its
  configuration at startup and exits immediately with this message rather
  than starting up broken. Check the `env` block in your MCP client's
  configuration.
- **Every call fails with a network error**: confirm the server process can
  actually reach `REDMINE_URL` — MCP clients run the server as a local
  process, so it needs the same network access as your machine, not the
  browser.
- **401 on every call**: the API key is wrong, or "Enable REST web service"
  is off in Redmine's settings.
- **403 on a specific tool**: usually a missing permission on the role of the
  user who owns the API key. `get_role` shows exactly which permissions a
  role has.
- **A tool responds 404 that you'd expect to work**: a few endpoints
  (`update_journal_note`, `update_news`/`delete_news`,
  `update_attachment`) were added in specific Redmine versions — see
  [docs/TOOLS.md](docs/TOOLS.md) for the minimum version of each.

## Security

See [SECURITY.md](SECURITY.md) for the full model. In short: an API key
grants access equivalent to the user who owns it, so create a dedicated
Redmine user with a role scoped to what you want the agent to do, and use
that user's key — don't try to limit the agent by editing this server's code.

**File uploads are disabled until you set `REDMINE_UPLOAD_ROOTS`.** The
three tools that upload a local file (`attach_file_to_issue`,
`attach_file_to_wiki_page`, `upload_project_file`) refuse every path by
default, precisely because an agent can be steered by injected content
(an issue comment, a wiki page) into uploading a file it was never meant to
read. See [SECURITY.md](SECURITY.md#file-uploads-prompt-injection-is-the-default-threat-model).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
