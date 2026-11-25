"""Prompt builders. No torch import, so the video server can share them."""

from __future__ import annotations

from .constants import CAMERA_MOTIONS, LIGHTING, LOCATIONS, PEOPLE, STYLES


def build_prompt(
    bag_type: str,
    color: str,
    location: str,
    lighting: str,
    style: str,
    people: str,
    extra: str,
) -> str:
    color_txt = f"{color.strip()} " if color.strip() else ""
    parts = [
        f"a {color_txt}{bag_type.lower()} for travel",
        LOCATIONS[location],
        LIGHTING[lighting],
        STYLES[style],
        PEOPLE[people],
        "highly detailed, 8k, photorealistic",
    ]
    if extra.strip():
        parts.insert(1, extra.strip())
    return ", ".join(parts)


def build_video_prompt(
    bag_type: str,
    color: str,
    location: str,
    lighting: str,
    style: str,
    people: str,
    motion: str,
) -> str:
    """Photo prompt + camera motion. Raises KeyError on an unknown option."""
    base = build_prompt(bag_type, color, location, lighting, style, people, extra="")
    return f"{base}, {CAMERA_MOTIONS[motion]}, smooth cinematic motion"
