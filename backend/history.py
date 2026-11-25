"""List previously generated PNGs (embedded metadata) and MP4s (.json sidecar)."""

from __future__ import annotations

import json

from PIL import Image

from .constants import OUTPUT_DIR
from .schemas import HistoryItem


def list_history(limit: int = 200) -> list[HistoryItem]:
    files = [*OUTPUT_DIR.glob("*.png"), *OUTPUT_DIR.glob("*.mp4")]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    out: list[HistoryItem] = []
    for f in files[:limit]:
        if f.suffix == ".mp4":
            out.append(_video_item(f))
            continue
        info: dict[str, str] = {}
        try:
            with Image.open(f) as im:
                info = dict(im.info)
        except Exception:
            pass
        seed_raw = info.get("seed")
        try:
            seed_val = int(seed_raw) if seed_raw is not None else None
        except ValueError:
            seed_val = None
        ref_name = info.get("reference_image")
        out.append(
            HistoryItem(
                filename=f.name,
                url=f"/outputs/{f.name}",
                prompt=info.get("prompt"),
                seed=seed_val,
                model=info.get("model"),
                reference_url=f"/outputs/refs/{ref_name}" if ref_name else None,
                created_at=f.stat().st_mtime,
            )
        )
    return out


def _video_item(f) -> HistoryItem:
    try:
        meta = json.loads(f.with_suffix(".json").read_text())
    except (OSError, ValueError):
        meta = {}
    return HistoryItem(
        filename=f.name,
        url=f"/outputs/{f.name}",
        prompt=meta.get("prompt"),
        kind="video",
        created_at=f.stat().st_mtime,
    )
