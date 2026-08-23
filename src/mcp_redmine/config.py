"""Environment-based configuration for the Redmine connection."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_TIMEOUT = 15.0

#: Repository root, when the package is used from a source checkout
#: (src/mcp_redmine/config.py -> src/mcp_redmine -> src -> repo root).
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _env_file_path() -> Path:
    """Return the .env file to read.

    Honours ``REDMINE_ENV_FILE`` for an explicit location; otherwise falls
    back to a ``.env`` beside the repository root, which is where the file
    lives in a source checkout. Installed copies have no such file, and the
    missing path is simply ignored by the caller.

    Returns:
        The path to try, which may not exist.
    """
    override = os.environ.get("REDMINE_ENV_FILE", "")
    if override:
        return Path(override)
    return _REPO_ROOT / ".env"


def _load_env_file() -> None:
    """Merge a local .env file into the process environment.

    Values already present in the environment win, so an MCP client's ``env``
    block still overrides the file. Missing files are not an error: the .env
    is an optional convenience, not the canonical configuration.
    """
    load_dotenv(_env_file_path(), override=False)


class ConfigurationError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    """Connection settings read from the environment.

    Attributes:
        url: Base URL of the Redmine instance, without a trailing slash.
        api_key: Redmine REST API key (My account > API access key).
        timeout: Per-request timeout in seconds.
        upload_roots: Directories local file uploads are allowed from. Empty
            means uploads are disabled — see `REDMINE_UPLOAD_ROOTS` in
            SECURITY.md.
        ssl_verify: Whether to verify the Redmine server's TLS certificate.
            Defaults to `True`; set `REDMINE_SSL_VERIFY=false` only for a
            trusted self-signed/internal cert you cannot otherwise validate —
            disabling it removes protection against man-in-the-middle
            attacks on that connection.
    """

    url: str
    api_key: str
    timeout: float = DEFAULT_TIMEOUT
    upload_roots: tuple[Path, ...] = ()
    ssl_verify: bool = True


_FALSE_VALUES = {"0", "false", "no", "off"}


def _parse_bool(raw: str, *, default: bool) -> bool:
    """Parse a boolean-flavoured environment variable.

    Args:
        raw: The raw environment value; blank means "unset".
        default: Value to use when `raw` is blank.

    Returns:
        `False` if `raw` (case-insensitively) is one of "0", "false", "no",
        "off"; `True` for any other non-blank value; `default` if blank.
    """
    if not raw:
        return default
    return raw.strip().lower() not in _FALSE_VALUES


def _parse_upload_roots(raw: str) -> tuple[Path, ...]:
    """Parse REDMINE_UPLOAD_ROOTS into resolved, validated directories.

    Args:
        raw: The raw environment value, entries separated by `os.pathsep`
            (`;` on Windows, `:` on POSIX — `:` would collide with a drive
            letter on Windows, which is why `os.pathsep` and not a literal
            `:` is used here).

    Returns:
        The resolved directories, in the order given. Empty if `raw` has no
        non-blank entries.

    Raises:
        ConfigurationError: If an entry does not resolve to an existing
            directory — better to fail at startup than to silently drop a
            root the operator expected to be active.
    """
    roots = []
    for entry in raw.split(os.pathsep):
        entry = entry.strip()
        if not entry:
            continue
        resolved = Path(entry).expanduser().resolve()
        if not resolved.is_dir():
            raise ConfigurationError(
                f"REDMINE_UPLOAD_ROOTS entry {entry!r} is not an existing directory."
            )
        roots.append(resolved)
    return tuple(roots)


def load_settings() -> Settings:
    """Read and validate settings from the environment.

    Loading is deferred to call time (rather than done at import time) so the
    package stays importable — for tests, tooling, or introspection — without
    REDMINE_URL and REDMINE_API_KEY being set.

    A local .env file is merged in first, without overriding variables that
    are already set; see `_load_env_file`.

    Returns:
        The validated settings.

    Raises:
        ConfigurationError: If REDMINE_URL or REDMINE_API_KEY is missing, if
            REDMINE_TIMEOUT is set but is not a positive number, or if
            REDMINE_UPLOAD_ROOTS has an entry that is not an existing
            directory.
    """
    _load_env_file()

    url = os.environ.get("REDMINE_URL", "").rstrip("/")
    api_key = os.environ.get("REDMINE_API_KEY", "")

    if not url or not api_key:
        raise ConfigurationError(
            "REDMINE_URL and REDMINE_API_KEY must be set in the environment. "
            "See .env.example, or the 'env' block of your MCP client's server "
            "configuration."
        )

    timeout = DEFAULT_TIMEOUT
    timeout_raw = os.environ.get("REDMINE_TIMEOUT", "")
    if timeout_raw:
        try:
            timeout = float(timeout_raw)
        except ValueError as exc:
            raise ConfigurationError(
                f"REDMINE_TIMEOUT must be a number, got {timeout_raw!r}."
            ) from exc
        if timeout <= 0:
            raise ConfigurationError("REDMINE_TIMEOUT must be greater than zero.")

    upload_roots = _parse_upload_roots(os.environ.get("REDMINE_UPLOAD_ROOTS", ""))
    ssl_verify = _parse_bool(os.environ.get("REDMINE_SSL_VERIFY", ""), default=True)

    return Settings(
        url=url,
        api_key=api_key,
        timeout=timeout,
        upload_roots=upload_roots,
        ssl_verify=ssl_verify,
    )
