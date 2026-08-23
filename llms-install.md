# Installing mcp-redmine (instructions for AI agents)

This file is written for an AI coding agent — Cline or similar — that is
setting this MCP server up on a user's machine. If you are a human, follow
[README.md](README.md) instead; it covers the same ground with more context.

This server exposes the Redmine REST API as 73 MCP tools over stdio. It is a
single Python process: no database, no service to host, no Docker.

## Before you start

Check these, and stop to ask the user if any is missing:

1. **Python 3.10 or newer** is installed and on the `PATH`.
2. The user has a **Redmine instance** with the REST API enabled
   (*Administration → Settings → API → "Enable REST web service"*).
3. The user has their **Redmine API key** (*My account → API access key*).

## Step 1 — Install the package

⚠️ **The distribution is `mcp-redmine-rest`, not `mcp-redmine`.** The shorter
name on PyPI belongs to [an unrelated project by a different
author](https://github.com/runekaagaard/mcp-redmine). Installing it will not
give you this server.

Preferred, if `uv` is available:

```bash
uv tool install mcp-redmine-rest
```

Otherwise:

```bash
pip install mcp-redmine-rest
```

Both install a console script named `mcp-redmine-rest`. Check that it resolves
before moving on — `which mcp-redmine-rest` on Linux/macOS, `where
mcp-redmine-rest` on Windows.

Do **not** try to verify by running the command: it takes no arguments and no
`--help`; it starts the MCP server and waits for protocol messages on stdin.

If the command does not resolve, the install went to an interpreter that is not
on the `PATH`. Don't guess — use the module form in Step 3 instead, pointing at
the interpreter you just installed into.

## Step 2 — Collect the configuration

The server reads these environment variables:

| Variable | Required | Value |
|---|---|---|
| `REDMINE_URL` | Yes | Base URL of the Redmine instance, no trailing slash — e.g. `https://redmine.example.com` |
| `REDMINE_API_KEY` | Yes | The user's API access key |
| `REDMINE_TIMEOUT` | No | Per-request timeout in seconds. Defaults to 15 |
| `REDMINE_UPLOAD_ROOTS` | No | Directories the file-upload tools may read from, separated by `os.pathsep`. **Leave unset unless the user asks for upload support** — see below |
| `REDMINE_SSL_VERIFY` | No | Verify the Redmine server's TLS certificate. Defaults to `true`. **Only set to `false` for a trusted self-signed/internal cert the user cannot otherwise validate** — it disables protection against man-in-the-middle attacks on that connection, so don't set it on your own initiative. |

**Ask the user for `REDMINE_URL` and `REDMINE_API_KEY`. Never invent, guess, or
carry over placeholder values** — a wrong URL fails with a network error and a
wrong key fails with 401 on every call, and neither is obvious from the
outside.

Treat the API key as a password: it grants exactly the access of the Redmine
user who owns it. Do not echo it back in chat, and do not commit it.

**Do not set `REDMINE_UPLOAD_ROOTS` on your own initiative.** File uploads
(`attach_file_to_issue`, `attach_file_to_wiki_page`, `upload_project_file`)
are refused by default — this is a deliberate defense against prompt
injection, not a gap to fill in during setup. Only configure it if the user
explicitly asks for upload support, and then only to directories the user
names themselves. See [SECURITY.md](SECURITY.md) before touching this.

## Step 3 — Write the client configuration

For **Cline**, open `cline_mcp_settings.json` (`Ctrl+Shift+P` → *Cline: Open
MCP Config File*, or the gear next to "MCP Servers" → *Configure MCP Servers*)
and add:

```json
{
  "mcpServers": {
    "redmine": {
      "command": "mcp-redmine-rest",
      "env": {
        "REDMINE_URL": "https://redmine.example.com",
        "REDMINE_API_KEY": "the_users_api_key"
      }
    }
  }
}
```

If Step 1 showed the console script is not on the `PATH`, use the module form
instead — same package, invoked through the interpreter it was installed into:

```json
{
  "mcpServers": {
    "redmine": {
      "command": "/full/path/to/python",
      "args": ["-m", "mcp_redmine"],
      "env": {
        "REDMINE_URL": "https://redmine.example.com",
        "REDMINE_API_KEY": "the_users_api_key"
      }
    }
  }
}
```

On Windows that path is typically `...\venv\Scripts\python.exe`, and JSON needs
the backslashes escaped (`\\`).

Other clients follow the same shape — see the Claude Desktop and Claude Code
sections of [README.md](README.md#claude-desktop).

### If the user prefers not to store the key in the client config

The server also reads a `.env` file, merging it into the environment **without**
overriding anything already set — so the client's `env` block still wins when
both exist. Copy `.env.example` to `.env` at the repository root, fill it in,
and drop the `env` block from the client configuration entirely. Set
`REDMINE_ENV_FILE` to keep that file somewhere else. The file is gitignored.

## Step 4 — Reload and verify

1. Reload the client so it launches the server — in VS Code, `Ctrl+Shift+P` →
   *Developer: Reload Window*.
2. Confirm the server shows up as connected, with its tools listed.
3. **Verify against the live instance**, not just the connection: call the
   `get_current_user` tool. It should return the Redmine account that owns the
   API key. This is the cheapest call that proves the URL, the key, and the
   permissions all work together.

Do not report the installation as successful until `get_current_user` returns a
real user. A connected server with a bad key still connects — it fails on the
first call.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `REDMINE_URL and REDMINE_API_KEY must be set` | The `env` block did not reach the process. Check for JSON syntax errors, and note that variable references like `${VAR}` are not reliably expanded — use literal values |
| Server starts, then every call returns 401 | Wrong API key, or "Enable REST web service" is off in Redmine |
| A specific tool returns 403 | The Redmine user owning the key lacks that permission. Call `get_role` to see what the user's role actually allows |
| Every call fails with a network error | The server process must reach `REDMINE_URL` itself — it runs locally, so check VPN, DNS, and firewall from that machine |
| `No module named 'mcp_redmine'` | The package is installed in a different interpreter than the one in `command`. Use the full path to the right interpreter |
| A tool returns 404 you did not expect | A few endpoints were added in specific Redmine versions. [docs/TOOLS.md](docs/TOOLS.md) lists the minimum version per tool |

## Things worth telling the user

- **The agent's permissions are the API key's permissions.** This server is a
  thin proxy and does not implement its own authorization — Redmine decides.
  To limit what the agent can do, create a dedicated Redmine user with a
  narrow role and use that user's key. See [SECURITY.md](SECURITY.md).
- **There is deliberately no `delete_project` and no `delete_user` tool.** Both
  are irreversible and take other people's content with them. Use
  `archive_project` and `update_user(status=3)` instead.
