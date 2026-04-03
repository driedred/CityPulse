from __future__ import annotations

import math
import re
from datetime import UTC, datetime
from difflib import SequenceMatcher

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def clamp(value: float, *, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def saturating_ratio(value: float, saturation_point: float) -> float:
    if saturation_point <= 0:
        return 0.0
    return clamp(value / saturation_point)


def normalize_text(value: str, *, max_length: int | None = None) -> str:
    normalized = re.sub(r"\s+", " ", value).strip()
    normalized = re.sub(r"([!?.,])\1+", r"\1", normalized)
    if max_length is not None:
        normalized = normalized[:max_length].strip()
    return normalized


def tokenize(value: str) -> set[str]:
    return set(TOKEN_PATTERN.findall(value.lower()))


def token_overlap_score(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    overlap = left & right
    union = left | right
    return len(overlap) / len(union)


def blended_text_similarity(
    *,
    title_left: str,
    title_right: str,
    description_left: str,
    description_right: str,
) -> float:
    normalized_title_left = normalize_text(title_left, max_length=160).lower()
    normalized_title_right = normalize_text(title_right, max_length=160).lower()
    normalized_description_left = normalize_text(description_left, max_length=4000).lower()
    normalized_description_right = normalize_text(description_right, max_length=4000).lower()

    title_similarity = SequenceMatcher(
        None,
        normalized_title_left,
        normalized_title_right,
    ).ratio()
    description_similarity = SequenceMatcher(
        None,
        normalized_description_left,
        normalized_description_right,
    ).ratio()
    token_similarity = token_overlap_score(
        tokenize(f"{normalized_title_left} {normalized_description_left}"),
        tokenize(f"{normalized_title_right} {normalized_description_right}"),
    )

    return clamp(
        title_similarity * 0.45
        + description_similarity * 0.2
        + token_similarity * 0.35
    )


def distance_km(
    lat_a: float,
    lon_a: float,
    lat_b: float,
    lon_b: float,
) -> float:
    radius_km = 6371.0
    lat_a_rad = math.radians(lat_a)
    lat_b_rad = math.radians(lat_b)
    delta_lat = math.radians(lat_b - lat_a)
    delta_lon = math.radians(lon_b - lon_a)

    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat_a_rad)
        * math.cos(lat_b_rad)
        * math.sin(delta_lon / 2) ** 2
    )
    return radius_km * 2 * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def round_public_people_estimate(value: float) -> int:
    if value <= 0:
        return 0
    if value < 50:
        return int(round(value / 5) * 5)
    if value < 250:
        return int(round(value / 10) * 10)
    return int(round(value / 25) * 25)
