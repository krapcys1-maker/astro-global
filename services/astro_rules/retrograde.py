from __future__ import annotations


def is_retrograde(speed_longitude_deg_per_day: float) -> bool:
    return speed_longitude_deg_per_day < 0.0


def station_proximity(speed_longitude_deg_per_day: float, threshold: float = 0.03) -> float:
    speed = abs(speed_longitude_deg_per_day)
    if speed >= threshold:
        return 0.0
    return 1.0 - (speed / threshold)

