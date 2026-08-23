"""Thin HTTP client for the Redmine REST API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import requests

from mcp_redmine.config import Settings
from mcp_redmine.errors import RedmineError, format_response_error


class RedmineClient:
    """A ``requests.Session`` bound to one Redmine instance and API key."""

    def __init__(self, settings: Settings) -> None:
        """Create a client from validated settings.

        Args:
            settings: Connection settings, as returned by
                :func:`mcp_redmine.config.load_settings`.
        """
        self._settings = settings
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-Redmine-API-Key": settings.api_key,
                "Content-Type": "application/json",
            }
        )

    @property
    def base_url(self) -> str:
        """Base URL of the Redmine instance, without a trailing slash."""
        return self._settings.url

    @property
    def api_key(self) -> str:
        """The configured Redmine API key."""
        return self._settings.api_key

    @property
    def upload_roots(self) -> tuple[Path, ...]:
        """Directories local file uploads are allowed from (empty = disabled)."""
        return self._settings.upload_roots

    @property
    def ssl_verify(self) -> bool:
        """Whether TLS certificate verification is enabled for this client."""
        return self._settings.ssl_verify

    def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Call the Redmine API and return the decoded JSON body.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE).
            path: Path relative to the Redmine base URL, e.g. "/issues.json".
            **kwargs: Passed through to ``requests.Session.request`` (params,
                json, and so on).

        Returns:
            The decoded JSON body, or an empty dict for empty responses (for
            example a 204 No Content).

        Raises:
            RedmineError: If the request fails at the network level, or if
                Redmine returns a non-2xx status.
        """
        url = f"{self._settings.url}{path}"
        try:
            response = self._session.request(
                method,
                url,
                timeout=self._settings.timeout,
                verify=self._settings.ssl_verify,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise RedmineError(f"network failure while calling Redmine: {exc}") from exc

        if not response.ok:
            raise RedmineError(format_response_error(response))

        if response.text.strip():
            result: dict[str, Any] = response.json()
            return result
        return {}
