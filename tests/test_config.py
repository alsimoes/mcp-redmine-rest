"""Tests for mcp_redmine.config."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from mcp_redmine.config import ConfigurationError, load_settings


def test_missing_url_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REDMINE_URL", raising=False)
    monkeypatch.setenv("REDMINE_API_KEY", "key")
    with pytest.raises(ConfigurationError):
        load_settings()


def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDMINE_URL", "https://redmine.example.com")
    monkeypatch.delenv("REDMINE_API_KEY", raising=False)
    with pytest.raises(ConfigurationError):
        load_settings()


def test_trailing_slash_is_stripped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDMINE_URL", "https://redmine.example.com/")
    monkeypatch.setenv("REDMINE_API_KEY", "key")
    monkeypatch.delenv("REDMINE_TIMEOUT", raising=False)
    settings = load_settings()
    assert settings.url == "https://redmine.example.com"


def test_default_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDMINE_URL", "https://redmine.example.com")
    monkeypatch.setenv("REDMINE_API_KEY", "key")
    monkeypatch.delenv("REDMINE_TIMEOUT", raising=False)
    settings = load_settings()
    assert settings.timeout == 15.0


def test_custom_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDMINE_URL", "https://redmine.example.com")
    monkeypatch.setenv("REDMINE_API_KEY", "key")
    monkeypatch.setenv("REDMINE_TIMEOUT", "30")
    settings = load_settings()
    assert settings.timeout == 30.0


def test_invalid_timeout_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDMINE_URL", "https://redmine.example.com")
    monkeypatch.setenv("REDMINE_API_KEY", "key")
    monkeypatch.setenv("REDMINE_TIMEOUT", "not-a-number")
    with pytest.raises(ConfigurationError):
        load_settings()


def test_zero_timeout_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDMINE_URL", "https://redmine.example.com")
    monkeypatch.setenv("REDMINE_API_KEY", "key")
    monkeypatch.setenv("REDMINE_TIMEOUT", "0")
    with pytest.raises(ConfigurationError):
        load_settings()


def test_env_file_supplies_missing_values(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "REDMINE_URL=https://from-file.example.com/\n"
        "REDMINE_API_KEY=file-key\n"
        "REDMINE_TIMEOUT=42\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("REDMINE_ENV_FILE", str(env_file))
    monkeypatch.delenv("REDMINE_URL", raising=False)
    monkeypatch.delenv("REDMINE_API_KEY", raising=False)
    monkeypatch.delenv("REDMINE_TIMEOUT", raising=False)

    settings = load_settings()

    assert settings.url == "https://from-file.example.com"
    assert settings.api_key == "file-key"
    assert settings.timeout == 42.0


def test_environment_wins_over_env_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("REDMINE_API_KEY=file-key\n", encoding="utf-8")
    monkeypatch.setenv("REDMINE_ENV_FILE", str(env_file))
    monkeypatch.setenv("REDMINE_URL", "https://redmine.example.com")
    monkeypatch.setenv("REDMINE_API_KEY", "env-key")
    monkeypatch.delenv("REDMINE_TIMEOUT", raising=False)

    settings = load_settings()

    assert settings.api_key == "env-key"


def test_upload_roots_default_to_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDMINE_URL", "https://redmine.example.com")
    monkeypatch.setenv("REDMINE_API_KEY", "key")
    monkeypatch.delenv("REDMINE_UPLOAD_ROOTS", raising=False)
    settings = load_settings()
    assert settings.upload_roots == ()


def test_upload_roots_single_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("REDMINE_URL", "https://redmine.example.com")
    monkeypatch.setenv("REDMINE_API_KEY", "key")
    monkeypatch.setenv("REDMINE_UPLOAD_ROOTS", str(tmp_path))
    settings = load_settings()
    assert settings.upload_roots == (tmp_path.resolve(),)


def test_upload_roots_multiple_directories_separated_by_pathsep(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root_a = tmp_path / "a"
    root_a.mkdir()
    root_b = tmp_path / "b"
    root_b.mkdir()
    monkeypatch.setenv("REDMINE_URL", "https://redmine.example.com")
    monkeypatch.setenv("REDMINE_API_KEY", "key")
    monkeypatch.setenv(
        "REDMINE_UPLOAD_ROOTS", os.pathsep.join([str(root_a), str(root_b)])
    )
    settings = load_settings()
    assert settings.upload_roots == (root_a.resolve(), root_b.resolve())


def test_upload_roots_expands_user_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("REDMINE_URL", "https://redmine.example.com")
    monkeypatch.setenv("REDMINE_API_KEY", "key")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    (tmp_path / "uploads").mkdir()
    monkeypatch.setenv("REDMINE_UPLOAD_ROOTS", os.path.join("~", "uploads"))
    settings = load_settings()
    assert settings.upload_roots == ((tmp_path / "uploads").resolve(),)


def test_upload_roots_nonexistent_directory_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("REDMINE_URL", "https://redmine.example.com")
    monkeypatch.setenv("REDMINE_API_KEY", "key")
    monkeypatch.setenv("REDMINE_UPLOAD_ROOTS", str(tmp_path / "does-not-exist"))
    with pytest.raises(ConfigurationError):
        load_settings()


def test_ssl_verify_defaults_to_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDMINE_URL", "https://redmine.example.com")
    monkeypatch.setenv("REDMINE_API_KEY", "key")
    monkeypatch.delenv("REDMINE_SSL_VERIFY", raising=False)
    settings = load_settings()
    assert settings.ssl_verify is True


@pytest.mark.parametrize("raw", ["false", "False", "0", "no", "off"])
def test_ssl_verify_falsy_values_disable_verification(
    monkeypatch: pytest.MonkeyPatch, raw: str
) -> None:
    monkeypatch.setenv("REDMINE_URL", "https://redmine.example.com")
    monkeypatch.setenv("REDMINE_API_KEY", "key")
    monkeypatch.setenv("REDMINE_SSL_VERIFY", raw)
    settings = load_settings()
    assert settings.ssl_verify is False


@pytest.mark.parametrize("raw", ["true", "True", "1", "yes", "on"])
def test_ssl_verify_truthy_values_enable_verification(
    monkeypatch: pytest.MonkeyPatch, raw: str
) -> None:
    monkeypatch.setenv("REDMINE_URL", "https://redmine.example.com")
    monkeypatch.setenv("REDMINE_API_KEY", "key")
    monkeypatch.setenv("REDMINE_SSL_VERIFY", raw)
    settings = load_settings()
    assert settings.ssl_verify is True


def test_missing_env_file_is_not_an_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("REDMINE_ENV_FILE", str(tmp_path / "absent.env"))
    monkeypatch.setenv("REDMINE_URL", "https://redmine.example.com")
    monkeypatch.setenv("REDMINE_API_KEY", "key")
    monkeypatch.delenv("REDMINE_TIMEOUT", raising=False)

    assert load_settings().api_key == "key"
