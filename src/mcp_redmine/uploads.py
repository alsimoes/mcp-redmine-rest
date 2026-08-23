"""Binary file uploads to the Redmine ``/uploads.json`` endpoint."""

from __future__ import annotations

import mimetypes
import os
from pathlib import Path

import requests

from mcp_redmine.client import RedmineClient
from mcp_redmine.errors import RedmineError, format_response_error

# Defensive limit. Redmine has its own, configurable in
# Administration -> Settings -> Files; this one just avoids discovering that
# limit only after pushing tens of megabytes over the network.
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

UPLOAD_TIMEOUT = 120.0

# Refused even inside an allowed root, as defense in depth. This is a
# heuristic, not the security boundary — REDMINE_UPLOAD_ROOTS is. See
# SECURITY.md.
_DENYLIST_NAMES = frozenset(
    {
        ".netrc",
        ".npmrc",
        ".pypirc",
        "credentials",
        "id_rsa",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
    }
)
_DENYLIST_SUFFIXES = frozenset({".pem", ".key", ".pfx", ".p12"})
_DENYLIST_DIR_NAMES = frozenset({".ssh", ".aws", ".gnupg", ".kube"})


def _matches_denylist(resolved: Path) -> bool:
    """Return whether a resolved path looks like a credential file.

    Args:
        resolved: An already-resolved, absolute path.

    Returns:
        True if the path's name, suffix, or an ancestor directory name
        matches a known credential-file pattern.
    """
    name = resolved.name
    if name.startswith(".env") or name in _DENYLIST_NAMES:
        return True
    if resolved.suffix in _DENYLIST_SUFFIXES:
        return True
    return bool(_DENYLIST_DIR_NAMES & set(resolved.parts))


def _check_upload_allowed(file_path: str, roots: tuple[Path, ...]) -> Path:
    """Resolve file_path and enforce the REDMINE_UPLOAD_ROOTS policy.

    This runs before any filesystem existence check. Checking existence
    first would let two distinguishable error messages ("not found" vs.
    "not allowed") act as an oracle for whether a path outside the
    allowlist exists on the server's disk — so the policy is decided purely
    from the resolved path, without touching the filesystem for anything
    other than resolving symlinks.

    Args:
        file_path: The path as given by the caller, not yet resolved.
        roots: Configured upload roots (already-resolved absolute
            directories). Empty means uploads are disabled.

    Returns:
        The resolved, allowed path.

    Raises:
        RedmineError: If uploads are disabled, the resolved path falls
            outside every configured root, or it matches the credential-file
            denylist.
    """
    if not roots:
        raise RedmineError(
            "file uploads are disabled: set REDMINE_UPLOAD_ROOTS to the "
            "directories this server may upload from. See SECURITY.md."
        )

    # .resolve() follows symlinks and collapses ".." segments, so a symlink
    # inside an allowed root that points outside it, or a "root/../../etc"
    # traversal, is judged by where it actually leads — not by its spelling.
    resolved = Path(file_path).expanduser().resolve()

    if not any(resolved.is_relative_to(root) for root in roots):
        # is_relative_to (not a string prefix check) so an allowed "/data"
        # does not also let in a sibling "/data-secreto".
        raise RedmineError(
            "path is outside the directories allowed by REDMINE_UPLOAD_ROOTS"
        )

    if _matches_denylist(resolved):
        raise RedmineError(
            f"'{resolved.name}' looks like a credential file and is refused "
            "even inside an allowed directory"
        )

    return resolved


def upload_file(
    client: RedmineClient, file_path: str, file_name: str = ""
) -> tuple[str, str, str]:
    """Upload a local file to ``/uploads.json`` and return its token.

    This bypasses ``RedmineClient.request`` because the upload requires
    ``Content-Type: application/octet-stream``, while the client's session
    headers are fixed to ``application/json``.

    The path is resolved on the machine running this MCP server, not on the
    machine of whoever calls the tool, and must fall within one of the
    directories configured through ``REDMINE_UPLOAD_ROOTS`` — uploads are
    refused by default. See SECURITY.md.

    Args:
        client: The Redmine client, used for its base URL, API key, and
            configured upload roots.
        file_path: Path to the local file to upload.
        file_name: Display name in Redmine (empty = use the file's own name).

    Returns:
        A ``(token, filename, content_type)`` tuple.

    Raises:
        RedmineError: If the path is not allowed by the upload policy, the
            file is missing, empty, larger than MAX_UPLOAD_BYTES, or the
            upload itself fails.
    """
    resolved = _check_upload_allowed(file_path, client.upload_roots)

    if not resolved.is_file():
        raise RedmineError(f"file not found: {file_path}")

    size = os.path.getsize(resolved)
    if size > MAX_UPLOAD_BYTES:
        megabytes = size / (1024 * 1024)
        raise RedmineError(
            f"file is {megabytes:.1f} MB, over this server's "
            f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit"
        )
    if size == 0:
        raise RedmineError("file is empty — Redmine rejects 0-byte uploads")

    name = file_name or resolved.name
    content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"

    headers = {
        "X-Redmine-API-Key": client.api_key,
        "Content-Type": "application/octet-stream",
    }

    try:
        with open(resolved, "rb") as handle:
            response = requests.post(
                f"{client.base_url}/uploads.json",
                headers=headers,
                data=handle,
                timeout=UPLOAD_TIMEOUT,
                verify=client.ssl_verify,
            )
    except requests.RequestException as exc:
        raise RedmineError(f"network failure during upload: {exc}") from exc
    except OSError as exc:
        raise RedmineError(f"could not read the file: {exc}") from exc

    if not response.ok:
        raise RedmineError(format_response_error(response))

    token = response.json().get("upload", {}).get("token")
    if not token:
        raise RedmineError("Redmine accepted the upload but returned no token")

    return token, name, content_type
