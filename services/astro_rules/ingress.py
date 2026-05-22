from __future__ import annotations

from services.astro_rules.angles import normalize_angle_deg


def distance_to_sign_boundary_deg(longitude_deg: float) -> float:
    degree = normalize_angle_deg(longitude_deg) % 30.0
    return min(degree, 30.0 - degree)


def ingress_proximity(longitude_deg: float, max_distance_deg: float = 2.0) -> float:
    distance = distance_to_sign_boundary_deg(longitude_deg)
    if distance >= max_distance_deg:
        return 0.0
    return 1.0 - (distance / max_distance_deg)
