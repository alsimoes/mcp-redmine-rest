"""Tests for mcp_redmine.uploads."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
import responses as responses_lib

from mcp_redmine.client import RedmineClient
from mcp_redmine.errors import RedmineError
from mcp_redmine.uploads import MAX_UPLOAD_BYTES, upload_file

# --- Case 1: no REDMINE_UPLOAD_ROOTS configured -----------------------------


def test_upload_disabled_by_default_touches_no_network(
    client: RedmineClient, mocked_responses: responses_lib.RequestsMock
) -> None:
    with pytest.raises(RedmineError, match="disabled"):
        upload_file(client, "/some/file.txt")
    assert len(mocked_responses.calls) == 0


# --- Case 2: file inside an allowed root ------------------------------------


def test_file_inside_allowed_root_uploads_normally(
    client_factory: Callable[..., RedmineClient],
    mocked_responses: responses_lib.RequestsMock,
    tmp_path: Path,
) -> None:
    client = client_factory(upload_roots=(tmp_path,))
    report = tmp_path / "report.pdf"
    report.write_bytes(b"%PDF-1.4 fake content")

    mocked_responses.add(
        responses_lib.POST,
        "https://redmine.example.com/uploads.json",
        json={"upload": {"token": "abc123.def456"}},
        status=201,
    )

    token, name, content_type = upload_file(client, str(report))

    assert token == "abc123.def456"
    assert name == "report.pdf"
    assert content_type == "application/pdf"


# --- Case 3: file outside every root -----------------------------------------


def test_file_outside_roots_is_rejected(
    client_factory: Callable[..., RedmineClient],
    mocked_responses: responses_lib.RequestsMock,
    tmp_path: Path,
) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"secret")

    client = client_factory(upload_roots=(allowed,))

    with pytest.raises(RedmineError, match="outside the directories"):
        upload_file(client, str(outside))
    assert len(mocked_responses.calls) == 0


# --- Case 4: traversal out of the root --------------------------------------


def test_traversal_out_of_root_is_rejected(
    client_factory: Callable[..., RedmineClient],
    mocked_responses: responses_lib.RequestsMock,
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    secret = tmp_path / "fora.txt"
    secret.write_bytes(b"secret")

    client = client_factory(upload_roots=(root,))
    traversal_path = str(root / ".." / "fora.txt")

    with pytest.raises(RedmineError, match="outside the directories"):
        upload_file(client, traversal_path)
    assert len(mocked_responses.calls) == 0


# --- Case 5: symlink inside the root pointing outside -----------------------


def test_symlink_inside_root_pointing_outside_is_rejected(
    client_factory: Callable[..., RedmineClient],
    mocked_responses: responses_lib.RequestsMock,
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_bytes(b"secret")
    link = root / "link.txt"
    try:
        link.symlink_to(secret)
    except OSError:
        pytest.skip("symlinks require elevated privileges on this platform")

    client = client_factory(upload_roots=(root,))

    with pytest.raises(RedmineError, match="outside the directories"):
        upload_file(client, str(link))
    assert len(mocked_responses.calls) == 0


# --- Case 6: nonexistent path outside the roots -----------------------------


def test_nonexistent_path_outside_roots_gets_policy_message(
    client_factory: Callable[..., RedmineClient],
    mocked_responses: responses_lib.RequestsMock,
    tmp_path: Path,
) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    client = client_factory(upload_roots=(allowed,))

    with pytest.raises(RedmineError, match="outside the directories") as exc_info:
        upload_file(client, str(tmp_path / "does-not-exist.txt"))

    assert "not found" not in str(exc_info.value)
    assert len(mocked_responses.calls) == 0


# --- Case 7: sibling directory with a matching string prefix ----------------


def test_sibling_directory_with_matching_prefix_is_not_inside_root(
    client_factory: Callable[..., RedmineClient],
    mocked_responses: responses_lib.RequestsMock,
    tmp_path: Path,
) -> None:
    root = tmp_path / "data"
    root.mkdir()
    sibling = tmp_path / "data-secreto"
    sibling.mkdir()
    leak = sibling / "x.txt"
    leak.write_bytes(b"secret")

    client = client_factory(upload_roots=(root,))

    with pytest.raises(RedmineError, match="outside the directories"):
        upload_file(client, str(leak))
    assert len(mocked_responses.calls) == 0


# --- Case 8: multiple roots separated by os.pathsep -------------------------


def test_accepts_file_in_any_of_several_configured_roots(
    client_factory: Callable[..., RedmineClient],
    mocked_responses: responses_lib.RequestsMock,
    tmp_path: Path,
) -> None:
    root_a = tmp_path / "a"
    root_a.mkdir()
    root_b = tmp_path / "b"
    root_b.mkdir()
    client = client_factory(upload_roots=(root_a, root_b))

    report = root_b / "report.txt"
    report.write_bytes(b"content")

    mocked_responses.add(
        responses_lib.POST,
        "https://redmine.example.com/uploads.json",
        json={"upload": {"token": "tok"}},
        status=201,
    )

    _token, name, _content_type = upload_file(client, str(report))
    assert name == "report.txt"


# --- Case 9: denylisted file inside an allowed root -------------------------


def test_denylist_rejects_env_file_even_inside_allowed_root(
    client_factory: Callable[..., RedmineClient],
    mocked_responses: responses_lib.RequestsMock,
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    secret = root / ".env"
    secret.write_text("REDMINE_API_KEY=whatever", encoding="utf-8")

    client = client_factory(upload_roots=(root,))

    with pytest.raises(RedmineError, match="credential file"):
        upload_file(client, str(secret))
    assert len(mocked_responses.calls) == 0


def test_denylist_rejects_ssh_key_even_inside_allowed_root(
    client_factory: Callable[..., RedmineClient],
    mocked_responses: responses_lib.RequestsMock,
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    ssh_dir = root / ".ssh"
    ssh_dir.mkdir(parents=True)
    key = ssh_dir / "id_rsa"
    key.write_text("fake key material", encoding="utf-8")

    client = client_factory(upload_roots=(root,))

    with pytest.raises(RedmineError, match="credential file"):
        upload_file(client, str(key))
    assert len(mocked_responses.calls) == 0


# --- Existing behavior, re-verified with an allowed root --------------------


def test_missing_file_is_rejected_before_touching_the_network(
    client_factory: Callable[..., RedmineClient],
    mocked_responses: responses_lib.RequestsMock,
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    client = client_factory(upload_roots=(root,))

    with pytest.raises(RedmineError, match="not found"):
        upload_file(client, str(root / "no-such-file.txt"))
    assert len(mocked_responses.calls) == 0


def test_empty_file_is_rejected(
    client_factory: Callable[..., RedmineClient], tmp_path: Path
) -> None:
    client = client_factory(upload_roots=(tmp_path,))
    empty_file = tmp_path / "empty.txt"
    empty_file.write_bytes(b"")
    with pytest.raises(RedmineError, match="empty"):
        upload_file(client, str(empty_file))


def test_oversized_file_is_rejected(
    client_factory: Callable[..., RedmineClient],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = client_factory(upload_roots=(tmp_path,))
    big_file = tmp_path / "big.bin"
    big_file.write_bytes(b"x")
    monkeypatch.setattr(
        "mcp_redmine.uploads.os.path.getsize", lambda _path: MAX_UPLOAD_BYTES + 1
    )
    with pytest.raises(RedmineError, match="MB"):
        upload_file(client, str(big_file))


def test_missing_token_in_response_raises(
    client_factory: Callable[..., RedmineClient],
    mocked_responses: responses_lib.RequestsMock,
    tmp_path: Path,
) -> None:
    client = client_factory(upload_roots=(tmp_path,))
    report = tmp_path / "report.txt"
    report.write_bytes(b"content")

    mocked_responses.add(
        responses_lib.POST,
        "https://redmine.example.com/uploads.json",
        json={"upload": {}},
        status=201,
    )

    with pytest.raises(RedmineError, match="no token"):
        upload_file(client, str(report))


def test_ssl_verify_false_is_forwarded_to_upload_request(
    client_factory: Callable[..., RedmineClient],
    mocked_responses: responses_lib.RequestsMock,
    tmp_path: Path,
) -> None:
    client = client_factory(upload_roots=(tmp_path,), ssl_verify=False)
    report = tmp_path / "report.txt"
    report.write_bytes(b"content")

    mocked_responses.add(
        responses_lib.POST,
        "https://redmine.example.com/uploads.json",
        json={"upload": {"token": "tok"}},
        status=201,
    )

    upload_file(client, str(report))

    assert mocked_responses.calls[0].request.req_kwargs["verify"] is False  # type: ignore[attr-defined]


def test_custom_file_name_overrides_basename(
    client_factory: Callable[..., RedmineClient],
    mocked_responses: responses_lib.RequestsMock,
    tmp_path: Path,
) -> None:
    client = client_factory(upload_roots=(tmp_path,))
    local_file = tmp_path / "tmp12345"
    local_file.write_bytes(b"content")

    mocked_responses.add(
        responses_lib.POST,
        "https://redmine.example.com/uploads.json",
        json={"upload": {"token": "tok"}},
        status=201,
    )

    _token, name, content_type = upload_file(client, str(local_file), "notes.txt")

    assert name == "notes.txt"
    assert content_type == "text/plain"
