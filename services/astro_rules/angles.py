from __future__ import annotations

import math


def normalize_angle_deg(value: float) -> float:
    normalized = value % 360.0
    if normalized < 0.0:
        normalized += 360.0
    return normalized


def angular_distance_deg(first: float, second: float) -> float:
    difference = abs(normalize_angle_deg(first) - normalize_angle_deg(second))
    return min(difference, 360.0 - difference)


def signed_angular_difference_deg(first: float, second: float) -> float:
    return (normalize_angle_deg(first) - normalize_angle_deg(second) + 180.0) % 360.0 - 180.0


def circular_features_deg(angle_deg: float) -> tuple[float, float]:
    angle_rad = math.radians(normalize_angle_deg(angle_deg))
    return math.cos(angle_rad), math.sin(angle_rad)
