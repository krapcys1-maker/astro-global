from __future__ import annotations

import argparse
import os
import secrets
import socket
from collections.abc import Mapping, Sequence

import uvicorn

LOCAL_API_HOST = "127.0.0.1"
SESSION_TOKEN_ENV = "ASTRO_GLOBAL_SESSION_TOKEN"
RUNTIME_ENV_ENV = "ASTRO_GLOBAL_ENV"
SESSION_TOKEN_HEADER = "x-astro-global-session"


def find_free_local_port(host: str = LOCAL_API_HOST) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def resolve_session_token(environ: Mapping[str, str] = os.environ) -> tuple[str, str]:
    existing = environ.get(SESSION_TOKEN_ENV, "").strip()
    if existing:
        return existing, "environment"
    runtime_environment = environ.get(RUNTIME_ENV_ENV, "development").strip().lower()
    if runtime_environment == "production":
        msg = f"{SESSION_TOKEN_ENV} is required when {RUNTIME_ENV_ENV}=production"
        raise ValueError(msg)
    return secrets.token_urlsafe(32), "generated"


def resolve_port(requested_port: int, host: str = LOCAL_API_HOST) -> int:
    if requested_port < 0 or requested_port > 65535:
        msg = "port must be between 0 and 65535"
        raise ValueError(msg)
    if requested_port == 0:
        return find_free_local_port(host)
    return requested_port


def build_startup_message(*, host: str, port: int, token_source: str) -> str:
    return "\n".join(
        (
            "Astro Global Core API",
            f"URL: http://{host}:{port}",
            f"Session token: {token_source}; value is not printed.",
            f"Auth header: {SESSION_TOKEN_HEADER}",
        )
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Astro Global local API safely.")
    parser.add_argument(
        "--host",
        default=LOCAL_API_HOST,
        help="Bind host. Only 127.0.0.1 is allowed for the local sidecar.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="Port to bind. Use 0 to choose a free local port.",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable uvicorn reload for local development.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    if args.host != LOCAL_API_HOST:
        msg = "Astro Global API runner only binds to 127.0.0.1."
        raise SystemExit(msg)
    port = resolve_port(args.port, args.host)
    token, token_source = resolve_session_token()
    os.environ[SESSION_TOKEN_ENV] = token
    print(build_startup_message(host=args.host, port=port, token_source=token_source), flush=True)
    uvicorn.run(
        "services.api.app:app",
        host=args.host,
        port=port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
