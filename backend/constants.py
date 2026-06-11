"""Static option sources shared by the API and the prompt builder."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "outputs"
CAMPAIGN_DIR = PROJECT_ROOT / "config" / "campaigns"

OUTPUT_DIR.mkdir(exist_ok=True)

MODELS = {
    "Fast & good — SDXL-Lightning (~7 GB download, recommended)": "lightning",
    "Small & light — SD 1.5 (~2 GB download, lower quality)": "sd15",
}

# SDXL resolutions per aspect ratio (SD 1.5 uses the half-size equivalents)
ASPECTS = {
    "Square 1:1  (Instagram post)": (1024, 1024),
    "Portrait 4:5  (Instagram feed)": (896, 1152),
    "Tall 9:16  (Stories / Reels)": (768, 1344),
    "Wide 16:9  (Website banner)": (1344, 768),
    "Landscape 3:2  (Print / catalog)": (1216, 832),
}

BAG_TYPES = [
    "Backpack",
    "Duffel bag",
    "Tote bag",
    "Carry-on suitcase",
    "Crossbody bag",
    "Hiking pack",
]

LOCATIONS = {
    "Photo studio (clean background)": "minimalist photo studio, seamless backdrop",
    "Mountain trail": "rocky mountain trail with distant peaks",
    "City street": "lively urban street, shallow depth of field",
    "Airport terminal": "modern airport terminal, large windows",
    "Beach": "quiet sandy beach near the waterline",
    "Coffee shop": "cozy coffee shop interior, wooden table",
    "Train station": "european train station platform",
}

LIGHTING = {
    "Soft studio light": "soft diffused studio lighting",
    "Golden hour": "warm golden hour sunlight, long shadows",
    "Overcast daylight": "soft overcast daylight",
    "Bright midday sun": "bright direct midday sunlight",
    "Evening / neon": "evening city lights, neon reflections",
}

STYLES = {
    "Product catalog (clean)": "professional product photography, sharp focus, commercial catalog style",
    "Lifestyle / candid": "candid lifestyle photography, natural and relatable",
    "Editorial / premium": "high-end editorial photography, premium magazine aesthetic",
    "Adventure / action": "dynamic outdoor adventure photography",
}

PEOPLE = {
    "No people — bag only": "no people, product only",
    "Hands only": "a person's hands holding the bag, hands visible only",
    "Person carrying it (back view)": "a traveler carrying the bag, seen from behind",
    "Person carrying it (side view)": "a traveler carrying the bag, side profile",
}

DEFAULT_NEGATIVE = (
    "watermark, text, caption, logo glitch, blurry, low quality, "
    "distorted, deformed, extra straps, extra limbs, bad anatomy, "
    "oversaturated, cartoon, illustration"
)
