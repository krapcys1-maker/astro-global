from __future__ import annotations

import socket

import pytest

from services.api.runner import (
    LOCAL_API_HOST,
    RUNTIME_ENV_ENV,
    SESSION_TOKEN_ENV,
    SESSION_TOKEN_HEADER,
    build_startup_message,
    find_free_local_port,
    parse_args,
    resolve_port,
    resolve_session_token,
)


def test_find_free_local_port_returns_bindable_port() -> None:
    port = find_free_local_port()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((LOCAL_API_HOST, port))


def test_resolve_session_token_prefers_environment_value() -> None:
    token, source = resolve_session_token({SESSION_TOKEN_ENV: "manual-token"})

    assert token == "manual-token"
    assert source == "environment"


def test_resolve_session_token_generates_secret_when_missing() -> None:
    token, source = resolve_session_token({})

    assert source == "generated"
    assert len(token) >= 32


def test_resolve_session_token_requires_environment_value_in_production() -> None:
    with pytest.raises(ValueError, match="ASTRO_GLOBAL_SESSION_TOKEN is required"):
        resolve_session_token({RUNTIME_ENV_ENV: "production"})


def test_startup_message_does_not_print_token_value() -> None:
    message = build_startup_message(
        host=LOCAL_API_HOST,
        port=8765,
        token_source="environment",
    )

    assert "http://127.0.0.1:8765" in message
    assert SESSION_TOKEN_HEADER in message
    assert "manual-token" not in message
    assert "value is not printed" in message


def test_parse_args_defaults_to_loopback_and_dynamic_port() -> None:
    args = parse_args([])

    assert args.host == LOCAL_API_HOST
    assert args.port == 0
    assert args.reload is False


def test_resolve_port_rejects_invalid_port() -> None:
    with pytest.raises(ValueError, match="port must be between"):
        resolve_port(70_000)
