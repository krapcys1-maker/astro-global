from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SESSION_TOKEN = "web-e2e-token"
LOCAL_HOST = "127.0.0.1"
WEB_PORT_CANDIDATES = (5173, 1420)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((LOCAL_HOST, 0))
        return int(sock.getsockname()[1])


def _is_port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((LOCAL_HOST, port)) == 0


def _pick_web_port() -> int:
    for port in WEB_PORT_CANDIDATES:
        if not _is_port_open(port):
            return port
    raise SystemExit("No allowed local web CORS port is free: 5173, 1420")


def _request(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
) -> tuple[int, dict[str, str], str]:
    data = None
    request_headers = headers or {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        request_headers = {"content-type": "application/json", **request_headers}
    request = urllib.request.Request(
        url,
        data=data,
        headers=request_headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return (
                int(response.status),
                {key.lower(): value for key, value in response.headers.items()},
                response.read().decode("utf-8"),
            )
    except urllib.error.HTTPError as exc:
        return (
            int(exc.code),
            {key.lower(): value for key, value in exc.headers.items()},
            exc.read().decode("utf-8"),
        )


def _wait_for(url: str, *, expected_status: int = 200, timeout_seconds: float = 20.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_status = "no response"
    while time.monotonic() < deadline:
        try:
            status, _, _ = _request(url)
            last_status = str(status)
            if status == expected_status:
                return
        except OSError as exc:
            last_status = str(exc)
        time.sleep(0.3)
    raise SystemExit(f"Timed out waiting for {url}; last status: {last_status}")


def _start_process(args: list[str], *, env: dict[str, str] | None = None) -> subprocess.Popen[str]:
    return subprocess.Popen(
        args,
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _terminate(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> None:
    api_port = _find_free_port()
    web_port = _pick_web_port()
    api_base = f"http://{LOCAL_HOST}:{api_port}"
    web_base = f"http://{LOCAL_HOST}:{web_port}"
    origin = web_base

    api_env = os.environ.copy()
    api_env["ASTRO_GLOBAL_SESSION_TOKEN"] = SESSION_TOKEN
    api_process = _start_process(
        [sys.executable, "scripts/run_api.py", "--port", str(api_port)],
        env=api_env,
    )
    web_process = _start_process(
        [sys.executable, "-m", "http.server", str(web_port), "-d", "web"],
    )

    try:
        _wait_for(f"{api_base}/health")
        _wait_for(f"{web_base}/index.html")

        web_status, _, web_body = _request(f"{web_base}/index.html")
        _assert(
            web_status == 200
            and "Astro Global" in web_body
            and "Silnik rezonansu historycznego" in web_body,
            "Web shell did not load.",
        )
        transparency_status, _, transparency_body = _request(f"{web_base}/transparency/")
        _assert(
            transparency_status == 200 and "Similarity is not prediction" in transparency_body,
            "Transparency page did not load.",
        )

        options_status, options_headers, _ = _request(
            f"{api_base}/data/status",
            method="OPTIONS",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "x-astro-global-session",
            },
        )
        _assert(options_status == 200, f"CORS preflight failed: {options_status}")
        _assert(
            options_headers.get("access-control-allow-origin") == origin,
            f"CORS did not allow web origin {origin}.",
        )

        status_code, status_headers, status_body = _request(
            f"{api_base}/data/status",
            headers={"Origin": origin, "x-astro-global-session": SESSION_TOKEN},
        )
        _assert(status_code == 200, f"/data/status failed: {status_body}")
        _assert(
            status_headers.get("access-control-allow-origin") == origin,
            "Actual CORS response does not include the web origin.",
        )
        runtime_status = json.loads(status_body)

        today_status, _, today_body = _request(
            f"{api_base}/today",
            headers={"Origin": origin, "x-astro-global-session": SESSION_TOKEN},
        )
        _assert(today_status == 200, f"/today failed: {today_body}")
        today_payload = json.loads(today_body)
        _assert(
            today_payload["recommended_search_request"]["provider"] == "swiss",
            "/today does not return a Swiss recommended search request.",
        )

        search_status, _, search_body = _request(
            f"{api_base}/resonance/search",
            method="POST",
            headers={"Origin": origin, "x-astro-global-session": SESSION_TOKEN},
            body={
                "date_utc": "2026-05-23T00:00:00Z",
                "profile_id": "global_slow_v1",
                "lookback_years": 120,
                "lookahead_years": 0,
                "step_days": 7,
                "top_k": 30,
                "max_episodes": 3,
                "events_per_episode": 4,
                "event_window_years": 1,
                "provider": "synthetic",
            },
        )
        _assert(search_status == 200, f"/resonance/search failed: {search_body}")
        search_payload = json.loads(search_body)
        _assert(search_payload.get("episodes"), "Search returned no episodes.")
        first_episode = search_payload["episodes"][0]
        _assert("matched_events" in first_episode, "Search response lacks matched_events.")
        _assert("context_events" in first_episode, "Search response lacks context_events.")
        _assert(
            "deterministic_summary" in search_payload,
            "Search response lacks deterministic_summary.",
        )
        _assert(
            "active_cycle_windows" in search_payload,
            "Search response lacks active_cycle_windows.",
        )
        _assert(
            "regime_cycle_windows" in search_payload,
            "Search response lacks regime_cycle_windows.",
        )

        compare_status, _, compare_body = _request(
            f"{api_base}/resonance/compare",
            method="POST",
            headers={"Origin": origin, "x-astro-global-session": SESSION_TOKEN},
            body={
                "left_date_utc": "2026-05-23T00:00:00Z",
                "right_date_utc": "2020-03-11T00:00:00Z",
                "profile_id": "global_slow_v1",
                "lookback_years": 3,
                "lookahead_years": 0,
                "step_days": 7,
                "top_k": 20,
                "max_episodes": 2,
                "events_per_episode": 4,
                "event_window_years": 1,
                "provider": "synthetic",
            },
        )
        _assert(compare_status == 200, f"/resonance/compare failed: {compare_body}")
        compare_payload = json.loads(compare_body)
        _assert(
            0.0 <= compare_payload["query_vector_similarity"] <= 1.0,
            "Compare response has invalid query_vector_similarity.",
        )
        _assert(
            "not a prediction" in " ".join(compare_payload["warnings"]),
            "Compare response lacks non-prediction warning.",
        )

        location_status, _, location_body = _request(
            f"{api_base}/locations/search?q=Warsz",
            headers={"Origin": origin, "x-astro-global-session": SESSION_TOKEN},
        )
        _assert(location_status == 200, f"/locations/search failed: {location_body}")
        location_payload = json.loads(location_body)
        _assert(location_payload, "Location search returned no results.")

        natal_status, _, natal_body = _request(
            f"{api_base}/natal-chart/calculate",
            method="POST",
            headers={"Origin": origin, "x-astro-global-session": SESSION_TOKEN},
            body={
                "birth_date": "1990-01-01",
                "birth_time": "12:00",
                "birthplace": "Warszawa",
                "country": "Poland",
                "house_system": "placidus",
                "zodiac_type": "tropical",
                "provider": "swiss",
            },
        )
        _assert(natal_status == 200, f"/natal-chart/calculate failed: {natal_body}")
        natal_payload = json.loads(natal_body)
        _assert(len(natal_payload["planets"]) == 10, "Natal chart lacks planet positions.")
        _assert(len(natal_payload["houses"]) == 12, "Natal chart lacks house cusps.")

        presets_status, _, presets_body = _request(
            f"{api_base}/resonance/compare/presets",
            headers={"Origin": origin, "x-astro-global-session": SESSION_TOKEN},
        )
        _assert(presets_status == 200, f"/resonance/compare/presets failed: {presets_body}")
        presets_payload = json.loads(presets_body)
        _assert(presets_payload.get("presets"), "Compare presets response is empty.")
        first_preset = presets_payload["presets"][0]
        _assert(
            first_preset["compare_request"]["provider"] == "swiss",
            "Compare preset does not return a Swiss compare request.",
        )

        article_seeds_status, _, article_seeds_body = _request(
            f"{api_base}/articles/seeds",
            headers={"Origin": origin, "x-astro-global-session": SESSION_TOKEN},
        )
        _assert(
            article_seeds_status == 200,
            f"/articles/seeds failed: {article_seeds_body}",
        )
        article_seeds_payload = json.loads(article_seeds_body)
        _assert(article_seeds_payload.get("seeds"), "Article seeds response is empty.")
        first_article_seed = article_seeds_payload["seeds"][0]
        _assert(
            first_article_seed["editorial_status"] == "seed_only_not_article",
            "Article seed is not marked seed-only.",
        )

        timeline_seeds_status, _, timeline_seeds_body = _request(
            f"{api_base}/timeline/seeds",
            headers={"Origin": origin, "x-astro-global-session": SESSION_TOKEN},
        )
        _assert(
            timeline_seeds_status == 200,
            f"/timeline/seeds failed: {timeline_seeds_body}",
        )
        timeline_seeds_payload = json.loads(timeline_seeds_body)
        _assert(timeline_seeds_payload.get("seeds"), "Timeline seeds response is empty.")
        first_timeline_seed = timeline_seeds_payload["seeds"][0]
        _assert(
            first_timeline_seed["search_request"]["provider"] == "swiss",
            "Timeline seed does not return a Swiss search request.",
        )
        _assert(
            "not a prediction" in " ".join(first_timeline_seed["warnings"]),
            "Timeline seed lacks non-prediction warning.",
        )

        print(
            json.dumps(
                {
                    "web_api_e2e": "ok",
                    "web_origin": origin,
                    "api_base": api_base,
                    "transparency": "ok",
                    "today_snapshot": today_payload["snapshot_date_utc"],
                    "runtime_environment": runtime_status["security"]["runtime_environment"],
                    "episodes": len(search_payload["episodes"]),
                    "compare_similarity": compare_payload["query_vector_similarity"],
                    "natal_planets": len(natal_payload["planets"]),
                    "compare_presets": len(presets_payload["presets"]),
                    "article_seeds": len(article_seeds_payload["seeds"]),
                    "timeline_seeds": len(timeline_seeds_payload["seeds"]),
                    "top_best_date": first_episode["best_date"],
                },
                indent=2,
            )
        )
    finally:
        _terminate(web_process)
        _terminate(api_process)


if __name__ == "__main__":
    main()
