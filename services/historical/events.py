from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

EVENT_SCHEMA_VERSION = "historical_event_v2"
EXPLICIT_END_YEAR_POLICY = "explicit"
ONGOING_END_YEAR_POLICY = "build_year"
END_YEAR_POLICIES = {EXPLICIT_END_YEAR_POLICY, ONGOING_END_YEAR_POLICY}


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


class HistoricalEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    display_date: str
    start_astro_year: int
    end_astro_year: int
    category: str
    event_kind: str
    region: str
    geo_scope: str
    source_url: HttpUrl
    confidence_score: float = Field(ge=0.0, le=1.0)
    is_ongoing: bool = False
    end_year_policy: str = EXPLICIT_END_YEAR_POLICY
    schema_version: str = EVENT_SCHEMA_VERSION

    @model_validator(mode="before")
    @classmethod
    def _infer_ongoing_fields(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        normalized = dict(data)
        display_date = str(normalized.get("display_date", "")).strip()
        is_open_ended = display_date.endswith("-")
        if normalized.get("is_ongoing") in {None, ""}:
            normalized["is_ongoing"] = is_open_ended
        if normalized.get("end_year_policy") in {None, ""}:
            normalized["end_year_policy"] = (
                ONGOING_END_YEAR_POLICY
                if _coerce_bool(normalized.get("is_ongoing"))
                else EXPLICIT_END_YEAR_POLICY
            )
        return normalized

    @field_validator(
        "id",
        "title",
        "display_date",
        "category",
        "event_kind",
        "region",
        "geo_scope",
        "end_year_policy",
    )
    @classmethod
    def _not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "field must not be blank"
            raise ValueError(msg)
        return stripped

    @model_validator(mode="after")
    def _validate_years_and_ongoing_policy(self) -> HistoricalEvent:
        if self.end_astro_year < self.start_astro_year:
            msg = "end_astro_year must be >= start_astro_year"
            raise ValueError(msg)
        if self.end_year_policy not in END_YEAR_POLICIES:
            msg = f"end_year_policy must be one of {sorted(END_YEAR_POLICIES)}"
            raise ValueError(msg)
        is_open_ended = self.display_date.endswith("-")
        if is_open_ended and not self.is_ongoing:
            msg = "open-ended display_date requires is_ongoing=true"
            raise ValueError(msg)
        if self.is_ongoing and self.end_year_policy != ONGOING_END_YEAR_POLICY:
            msg = "ongoing events require end_year_policy=build_year"
            raise ValueError(msg)
        if not self.is_ongoing and self.end_year_policy != EXPLICIT_END_YEAR_POLICY:
            msg = "non-ongoing events require end_year_policy=explicit"
            raise ValueError(msg)
        return self


class EventSource(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    event_id: str
    source_type: str
    source_name: str
    source_url: HttpUrl
    source_quality: str
    source_precision: str = "direct"

    @field_validator(
        "id",
        "event_id",
        "source_type",
        "source_name",
        "source_quality",
        "source_precision",
    )
    @classmethod
    def _not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "field must not be blank"
            raise ValueError(msg)
        return stripped
