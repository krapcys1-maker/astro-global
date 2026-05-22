from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from services.astro_rules.aspects import AspectHit

CYCLE_REGISTRY_PATH = Path(__file__).with_name("cycle_registry.yaml")


class CycleDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    pair: tuple[str, str]
    cycle_years: float
    tier: str
    tier_weight: float
    interpretation_role: str


class CycleContribution(BaseModel):
    model_config = ConfigDict(frozen=True)

    pair: tuple[str, str]
    aspect: str
    phase_role: str
    orb_deg: float
    closeness: float
    cycle_years: float
    tier: str
    tier_weight: float
    phase_weight: float
    contribution: float
    role: str


def normalize_pair(first: str, second: str) -> tuple[str, str]:
    pair = sorted((first, second))
    return pair[0], pair[1]


@lru_cache(maxsize=1)
def load_cycle_registry(path: Path = CYCLE_REGISTRY_PATH) -> dict[tuple[str, str], CycleDefinition]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    definitions: dict[tuple[str, str], CycleDefinition] = {}
    for raw_pair, payload in raw["cycles"].items():
        first, second = raw_pair.split("-", maxsplit=1)
        pair = normalize_pair(first, second)
        definitions[pair] = CycleDefinition(pair=pair, **payload)
    return definitions


def cycle_for_pair(first: str, second: str) -> CycleDefinition | None:
    return load_cycle_registry().get(normalize_pair(first, second))


def cycle_contribution_from_aspect(
    aspect: AspectHit,
    evidence_confidence_cap: float = 1.0,
) -> CycleContribution | None:
    definition = cycle_for_pair(aspect.body_a, aspect.body_b)
    if definition is None:
        return None
    confidence = max(0.0, min(1.0, evidence_confidence_cap))
    contribution = definition.tier_weight * aspect.phase_weight * aspect.closeness * confidence
    role = (
        "primary"
        if definition.tier in {"S_epochal", "A_structural"} and aspect.phase_role == "hard"
        else "supporting"
    )
    return CycleContribution(
        pair=definition.pair,
        aspect=aspect.aspect,
        phase_role=aspect.phase_role,
        orb_deg=aspect.orb_deg,
        closeness=aspect.closeness,
        cycle_years=definition.cycle_years,
        tier=definition.tier,
        tier_weight=definition.tier_weight,
        phase_weight=aspect.phase_weight,
        contribution=contribution,
        role=role,
    )
