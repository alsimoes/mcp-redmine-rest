"""Tests for mcp_redmine.client and mcp_redmine.errors."""

from __future__ import annotations

import pytest
import requests
import responses as responses_lib

from mcp_redmine.client import RedmineClient
from mcp_redmine.config import Settings
from mcp_redmine.errors import RedmineError, format_response_error


@pytest.fixture
def redmine_client() -> RedmineClient:
    return RedmineClient(Settings(url="https://redmine.example.com", api_key="key"))


def test_successful_get_returns_json(
    redmine_client: RedmineClient, mocked_responses: responses_lib.RequestsMock
) -> None:
    mocked_responses.add(
        responses_lib.GET,
        "https://redmine.example.com/issues.json",
        json={"issues": [{"id": 1}]},
        status=200,
    )
    data = redmine_client.request("GET", "/issues.json")
    assert data == {"issues": [{"id": 1}]}


def test_empty_body_returns_empty_dict(
    redmine_client: RedmineClient, mocked_responses: responses_lib.RequestsMock
) -> None:
    mocked_responses.add(
        responses_lib.DELETE,
        "https://redmine.example.com/issues/1.json",
        body="",
        status=204,
    )
    assert redmine_client.request("DELETE", "/issues/1.json") == {}


def test_sends_api_key_header(
    redmine_client: RedmineClient, mocked_responses: responses_lib.RequestsMock
) -> None:
    mocked_responses.add(
        responses_lib.GET,
        "https://redmine.example.com/users/current.json",
        json={"user": {}},
        status=200,
    )
    redmine_client.request("GET", "/users/current.json")
    assert mocked_responses.calls[0].request.headers["X-Redmine-API-Key"] == "key"


@pytest.mark.parametrize(
    ("status", "expected_fragment"),
    [
        (401, "invalid or missing API key"),
        (403, "not allowed"),
        (404, "not found"),
        (409, "conflict"),
        (422, "rejected the data"),
    ],
)
def test_known_status_codes_get_a_reason(
    redmine_client: RedmineClient,
    mocked_responses: responses_lib.RequestsMock,
    status: int,
    expected_fragment: str,
) -> None:
    mocked_responses.add(
        responses_lib.GET,
        "https://redmine.example.com/issues/1.json",
        json={},
        status=status,
    )
    with pytest.raises(RedmineError) as exc_info:
        redmine_client.request("GET", "/issues/1.json")
    assert expected_fragment in str(exc_info.value)


def test_validation_errors_are_extracted_from_body(
    redmine_client: RedmineClient, mocked_responses: responses_lib.RequestsMock
) -> None:
    mocked_responses.add(
        responses_lib.POST,
        "https://redmine.example.com/issues.json",
        json={"errors": ["Subject cannot be blank"]},
        status=422,
    )
    with pytest.raises(RedmineError) as exc_info:
        redmine_client.request("POST", "/issues.json", json={})
    assert "Subject cannot be blank" in str(exc_info.value)


def test_ssl_verify_defaults_to_true(
    redmine_client: RedmineClient, mocked_responses: responses_lib.RequestsMock
) -> None:
    mocked_responses.add(
        responses_lib.GET,
        "https://redmine.example.com/issues.json",
        json={},
        status=200,
    )
    redmine_client.request("GET", "/issues.json")
    assert mocked_responses.calls[0].request.req_kwargs["verify"] is True  # type: ignore[attr-defined]


def test_ssl_verify_false_is_forwarded_to_requests(
    mocked_responses: responses_lib.RequestsMock,
) -> None:
    client = RedmineClient(
        Settings(url="https://redmine.example.com", api_key="key", ssl_verify=False)
    )
    mocked_responses.add(
        responses_lib.GET,
        "https://redmine.example.com/issues.json",
        json={},
        status=200,
    )
    client.request("GET", "/issues.json")
    assert mocked_responses.calls[0].request.req_kwargs["verify"] is False  # type: ignore[attr-defined]


def test_network_failure_is_wrapped(
    redmine_client: RedmineClient, mocked_responses: responses_lib.RequestsMock
) -> None:
    mocked_responses.add(
        responses_lib.GET,
        "https://redmine.example.com/issues.json",
        body=requests.exceptions.ConnectionError("boom"),
    )
    with pytest.raises(RedmineError, match="network failure"):
        redmine_client.request("GET", "/issues.json")


def test_format_response_error_falls_back_to_status_when_no_reason_known() -> None:
    class FakeResponse:
        status_code = 418

        def json(self) -> dict[str, object]:
            raise ValueError("not json")

    assert format_response_error(FakeResponse()) == "HTTP 418"  # type: ignore[arg-type]
