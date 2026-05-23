from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from services.narrative.article_draft import ArticleDraftFactPack, ArticleDraftOutput

LLM_BASE_URL_ENV = "ASTRO_GLOBAL_LLM_BASE_URL"
LLM_API_KEY_ENV = "ASTRO_GLOBAL_LLM_API_KEY"
LLM_MODEL_ENV = "ASTRO_GLOBAL_LLM_MODEL"
LLM_TIMEOUT_SECONDS_ENV = "ASTRO_GLOBAL_LLM_TIMEOUT_SECONDS"
LLM_TEMPERATURE_ENV = "ASTRO_GLOBAL_LLM_TEMPERATURE"
DEEPSEEK_API_KEY_ENV = "DEEPSEEK_API_KEY"
DEEPSEEK_BASE_URL_ENV = "DEEPSEEK_BASE_URL"
DEEPSEEK_MODEL_ENV = "DEEPSEEK_MODEL"
DEFAULT_ENV_FILE = ".env"
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"
DEFAULT_LLM_TIMEOUT_SECONDS = 60.0
DEFAULT_LLM_TEMPERATURE = 0.2


class ArticleDraftLLMError(RuntimeError):
    pass


class ArticleDraftTransport(Protocol):
    def __call__(
        self,
        *,
        base_url: str,
        api_key: str,
        payload: dict[str, Any],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        pass


@dataclass(frozen=True)
class ArticleDraftLiveConfig:
    base_url: str
    api_key: str
    model: str
    timeout_seconds: float = DEFAULT_LLM_TIMEOUT_SECONDS
    temperature: float = DEFAULT_LLM_TEMPERATURE

    def public_summary(self) -> dict[str, Any]:
        return {
            "base_url": self.base_url,
            "model": self.model,
            "timeout_seconds": self.timeout_seconds,
            "temperature": self.temperature,
        }


def load_article_draft_live_config_from_env(
    *,
    env_file: Path | str | None = DEFAULT_ENV_FILE,
) -> ArticleDraftLiveConfig:
    env = _merged_env(env_file)
    deepseek_api_key = _env_value(env, DEEPSEEK_API_KEY_ENV)
    api_key = _env_value(env, LLM_API_KEY_ENV) or deepseek_api_key
    base_url = (
        _env_value(env, LLM_BASE_URL_ENV)
        or _env_value(env, DEEPSEEK_BASE_URL_ENV)
        or (DEFAULT_DEEPSEEK_BASE_URL if deepseek_api_key else "")
    )
    model = (
        _env_value(env, LLM_MODEL_ENV)
        or _env_value(env, DEEPSEEK_MODEL_ENV)
        or (DEFAULT_DEEPSEEK_MODEL if deepseek_api_key else "")
    )
    missing = []
    if not base_url:
        missing.append(f"{LLM_BASE_URL_ENV} or {DEEPSEEK_BASE_URL_ENV}")
    if not api_key:
        missing.append(f"{LLM_API_KEY_ENV} or {DEEPSEEK_API_KEY_ENV}")
    if not model:
        missing.append(f"{LLM_MODEL_ENV} or {DEEPSEEK_MODEL_ENV}")
    if missing:
        raise ArticleDraftLLMError(
            "Live LLM mode requires env vars: " + ", ".join(missing)
        )
    return ArticleDraftLiveConfig(
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout_seconds=_float_env(
            LLM_TIMEOUT_SECONDS_ENV,
            default=DEFAULT_LLM_TIMEOUT_SECONDS,
            env=env,
        ),
        temperature=_float_env(
            LLM_TEMPERATURE_ENV,
            default=DEFAULT_LLM_TEMPERATURE,
            env=env,
        ),
    )


def build_article_draft_messages(fact_pack: ArticleDraftFactPack) -> tuple[dict[str, str], ...]:
    schema_hint = {
        "seed_id": fact_pack.seed_id,
        "title": "string",
        "language": "pl",
        "content_policy": fact_pack.output_policy,
        "editorial_status": fact_pack.editorial_status_required,
        "sections": [
            {
                "section_id": "string",
                "heading": "string",
                "paragraphs": ["string"],
                "claims": [
                    {
                        "claim_id": "string",
                        "text": "string",
                        "event_ids": ["evt_id_from_allowed_event_ids"],
                        "source_ids": ["src_id_from_allowed_source_ids"],
                        "cycle_labels": ["cycle_label_from_shared_primary_cycles"],
                    }
                ],
            }
        ],
        "used_event_ids": ["evt_id_from_allowed_event_ids"],
        "used_source_ids": ["src_id_from_allowed_source_ids"],
        "warnings": ["draft_needs_human_review"],
    }
    system = (
        "Jestes lokalnym asystentem redakcyjnym Astro Global. Pisz po polsku. "
        "Nie jestes zrodlem faktow. Nie wolno dodawac wydarzen, zrodel, dat ani "
        "twierdzen spoza przekazanego fact-packa. Oddzielaj matched events od "
        "context events. Nie pisz prognoz. Zwroc wylacznie poprawny JSON zgodny "
        "ze schematem ArticleDraftOutput. Pisz jak evidence ledger: kazde zdanie "
        "faktograficzne ma wynikac z tytulu, daty, roli, kategorii albo warningu "
        "obecnego w fact-packu. Nie dopowiadaj motywacji, ideologii, skutkow, "
        "przyczyn ani interpretacji, jesli nie sa jawnie w fact-packu."
    )
    user = {
        "task": (
            "Napisz krotki szkic artykulu do review czlowieka. Uzywaj tylko "
            "allowed_event_ids, allowed_source_ids i shared_primary_cycles z fact-packa. "
            "Nie wyjasniaj historii szerzej niz pozwala fact-pack: wolno streszczac "
            "tytuly, daty, role matched/context, score_label, narrative_confidence, "
            "query_vector_similarity i warningi; nie wolno dodawac ideologii, "
            "postulatow, skutkow ani zwiazkow przyczynowych spoza tych pol."
        ),
        "required_output_schema": schema_hint,
        "fact_pack": fact_pack.model_dump(mode="json"),
    }
    return (
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
    )


def generate_live_article_draft(
    *,
    fact_pack: ArticleDraftFactPack,
    config: ArticleDraftLiveConfig,
    transport: ArticleDraftTransport | None = None,
) -> tuple[ArticleDraftOutput, str]:
    payload = {
        "model": config.model,
        "messages": list(build_article_draft_messages(fact_pack)),
        "temperature": config.temperature,
        "response_format": {"type": "json_object"},
    }
    response = (transport or _post_openai_compatible_chat_completion)(
        base_url=config.base_url,
        api_key=config.api_key,
        payload=payload,
        timeout_seconds=config.timeout_seconds,
    )
    raw_content = _extract_chat_completion_content(response)
    return parse_article_draft_output(raw_content), raw_content


def parse_article_draft_output(raw_content: str) -> ArticleDraftOutput:
    cleaned = _strip_json_fence(raw_content.strip())
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ArticleDraftLLMError("LLM response was not valid JSON.") from exc
    try:
        return ArticleDraftOutput.model_validate(payload)
    except ValueError as exc:
        raise ArticleDraftLLMError("LLM JSON did not match ArticleDraftOutput.") from exc


def _post_openai_compatible_chat_completion(
    *,
    base_url: str,
    api_key: str,
    payload: dict[str, Any],
    timeout_seconds: float,
) -> dict[str, Any]:
    request = urllib.request.Request(
        base_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise ArticleDraftLLMError(
            f"LLM provider returned HTTP {exc.code}: {error_body[:500]}"
        ) from exc
    except urllib.error.URLError as exc:
        raise ArticleDraftLLMError(f"LLM provider request failed: {exc}") from exc
    try:
        return dict(json.loads(body))
    except json.JSONDecodeError as exc:
        raise ArticleDraftLLMError("LLM provider response was not JSON.") from exc


def _extract_chat_completion_content(response: dict[str, Any]) -> str:
    try:
        choices = response["choices"]
        first_choice = choices[0]
        message = first_choice["message"]
        content = message["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ArticleDraftLLMError("LLM response lacks choices[0].message.content.") from exc
    if not isinstance(content, str) or not content.strip():
        raise ArticleDraftLLMError("LLM response content is empty.")
    return content


def _strip_json_fence(raw_content: str) -> str:
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", raw_content, flags=re.DOTALL)
    if match:
        return match.group(1)
    return raw_content


def _merged_env(env_file: Path | str | None) -> dict[str, str]:
    env = _read_env_file(env_file)
    env.update({key: value for key, value in os.environ.items() if value is not None})
    return env


def _read_env_file(env_file: Path | str | None) -> dict[str, str]:
    if env_file is None:
        return {}
    path = Path(env_file)
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", maxsplit=1)
        key = key.strip()
        if not key:
            continue
        values[key] = _strip_env_value(raw_value.strip())
    return values


def _strip_env_value(raw_value: str) -> str:
    if (
        len(raw_value) >= 2
        and raw_value[0] == raw_value[-1]
        and raw_value[0] in {"'", '"'}
    ):
        return raw_value[1:-1]
    return raw_value


def _env_value(env: dict[str, str], name: str) -> str:
    return env.get(name, "").strip()


def _float_env(name: str, *, default: float, env: dict[str, str]) -> float:
    raw = _env_value(env, name)
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ArticleDraftLLMError(f"{name} must be a number.") from exc
    if value <= 0.0:
        raise ArticleDraftLLMError(f"{name} must be > 0.")
    return value
