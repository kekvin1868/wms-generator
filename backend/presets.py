"""Load YAML campaign presets from config/campaigns/."""

from typing import Any

import yaml

from .constants import CAMPAIGN_DIR


def load_presets() -> dict[str, dict[str, Any] | None]:
    presets: dict[str, dict[str, Any] | None] = {"— Start from scratch —": None}
    if CAMPAIGN_DIR.exists():
        for f in sorted(CAMPAIGN_DIR.glob("*.yaml")):
            try:
                data = yaml.safe_load(f.read_text())
                presets[data.get("name", f.stem)] = data
            except Exception:
                pass
    return presets
