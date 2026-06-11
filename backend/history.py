"""List previously generated PNGs and read their embedded metadata."""

from __future__ import annotations

from PIL import Image

from .constants import OUTPUT_DIR
from .schemas import HistoryItem


def list_history(limit: int = 200) -> list[HistoryItem]:
    files = sorted(OUTPUT_DIR.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    out: list[HistoryItem] = []
    for f in files[:limit]:
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
        out.append(
            HistoryItem(
                filename=f.name,
                url=f"/outputs/{f.name}",
                prompt=info.get("prompt"),
                seed=seed_val,
                model=info.get("model"),
                created_at=f.stat().st_mtime,
            )
        )
    return out
