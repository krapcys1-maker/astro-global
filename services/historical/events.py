from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

EVENT_SCHEMA_VERSION = "historical_event_v1"


class HistoricalEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    display_date: str
    start_astro_year: int
    end_astro_year: int
    category: str
    region: str
    geo_scope: str
    source_url: HttpUrl
    confidence_score: float = Field(ge=0.0, le=1.0)
    schema_version: str = EVENT_SCHEMA_VERSION

    @field_validator("id", "title", "display_date", "category", "region", "geo_scope")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "field must not be blank"
            raise ValueError(msg)
        return stripped

    @model_validator(mode="after")
    def _end_after_start(self) -> HistoricalEvent:
        if self.end_astro_year < self.start_astro_year:
            msg = "end_astro_year must be >= start_astro_year"
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

    @field_validator("id", "event_id", "source_type", "source_name", "source_quality")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "field must not be blank"
            raise ValueError(msg)
        return stripped
