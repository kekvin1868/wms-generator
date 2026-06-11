"""
Travel Bag Co. — AI Image Studio (local prototype)

One screen. Pick options from dropdowns, press the big button.
Models download automatically on first use (one-time wait).

Run:  python app.py
"""

import os
import re
import datetime
from pathlib import Path

import torch
import yaml
import gradio as gr
from PIL import PngImagePlugin

# ----------------------------------------------------------------------------
# Device: Apple Silicon (MPS) -> half precision; otherwise CPU fallback
# ----------------------------------------------------------------------------
if torch.backends.mps.is_available():
    DEVICE, DTYPE = "mps", torch.float16
elif torch.cuda.is_available():
    DEVICE, DTYPE = "cuda", torch.float16
else:
    DEVICE, DTYPE = "cpu", torch.float32

OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)
CAMPAIGN_DIR = Path(__file__).parent / "config" / "campaigns"

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

BAG_TYPES = ["Backpack", "Duffel bag", "Tote bag", "Carry-on suitcase",
             "Crossbody bag", "Hiking pack"]

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

DEFAULT_NEGATIVE = ("watermark, text, caption, logo glitch, blurry, low quality, "
                    "distorted, deformed, extra straps, extra limbs, bad anatomy, "
                    "oversaturated, cartoon, illustration")

# ----------------------------------------------------------------------------
# Campaign presets (loaded from config/campaigns/*.yaml)
# ----------------------------------------------------------------------------
def load_presets():
    presets = {"— Start from scratch —": None}
    if CAMPAIGN_DIR.exists():
        for f in sorted(CAMPAIGN_DIR.glob("*.yaml")):
            try:
                data = yaml.safe_load(f.read_text())
                presets[data.get("name", f.stem)] = data
            except Exception:
                pass
    return presets

PRESETS = load_presets()

# ----------------------------------------------------------------------------
# Model loading (lazy, cached)
# ----------------------------------------------------------------------------
_PIPES = {}

def get_pipeline(model_key, progress=None):
    if model_key in _PIPES:
        return _PIPES[model_key]

    if progress:
        progress(0.05, desc="First-time model download — this can take a while. "
                            "Watch the Terminal window for a progress bar.")

    if model_key == "lightning":
        from diffusers import StableDiffusionXLPipeline, EulerDiscreteScheduler
        from huggingface_hub import hf_hub_download
        ckpt = hf_hub_download("ByteDance/SDXL-Lightning",
                               "sdxl_lightning_4step.safetensors")
        pipe = StableDiffusionXLPipeline.from_single_file(ckpt, torch_dtype=DTYPE)
        pipe.scheduler = EulerDiscreteScheduler.from_config(
            pipe.scheduler.config, timestep_spacing="trailing")
    else:  # sd15
        from diffusers import StableDiffusionPipeline
        pipe = StableDiffusionPipeline.from_pretrained(
            "stable-diffusion-v1-5/stable-diffusion-v1-5",
            torch_dtype=DTYPE, safety_checker=None, requires_safety_checker=False)

    pipe = pipe.to(DEVICE)
    pipe.enable_attention_slicing()
    _PIPES[model_key] = pipe
    return pipe

# ----------------------------------------------------------------------------
# Prompt assembly
# ----------------------------------------------------------------------------
def build_prompt(bag_type, color, location, lighting, style, people, extra):
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

def safe_name(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:30]

# ----------------------------------------------------------------------------
# Generation
# ----------------------------------------------------------------------------
def generate(model_label, bag_type, color, location, lighting, style, people,
             extra, aspect, count, seed_text,
             progress=gr.Progress()):
    model_key = MODELS[model_label]
    pipe = get_pipeline(model_key, progress)

    w, h = ASPECTS[aspect]
    if model_key == "sd15":          # SD 1.5 native resolution is ~512px
        w, h = max(512, w // 2 // 8 * 8), max(512, h // 2 // 8 * 8)

    prompt = build_prompt(bag_type, color, location, lighting, style, people, extra)

    try:
        seed = int(seed_text)
    except (TypeError, ValueError):
        seed = torch.seed() % (2**32)

    images, paths = [], []
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    for i in range(int(count)):
        progress((i + 1) / int(count),
                 desc=f"Creating image {i + 1} of {int(count)}…")
        gen = torch.Generator("cpu").manual_seed(seed + i)

        if model_key == "lightning":
            img = pipe(prompt, negative_prompt=DEFAULT_NEGATIVE,
                       num_inference_steps=4, guidance_scale=0.0,
                       width=w, height=h, generator=gen).images[0]
        else:
            img = pipe(prompt, negative_prompt=DEFAULT_NEGATIVE,
                       num_inference_steps=25, guidance_scale=7.0,
                       width=w, height=h, generator=gen).images[0]

        meta = PngImagePlugin.PngInfo()
        meta.add_text("prompt", prompt)
        meta.add_text("negative_prompt", DEFAULT_NEGATIVE)
        meta.add_text("seed", str(seed + i))
        meta.add_text("model", model_key)

        fname = (f"{safe_name(bag_type)}_{safe_name(location)}_"
                 f"{safe_name(lighting)}_seed{seed + i}_{stamp}.png")
        path = OUTPUT_DIR / fname
        img.save(path, pnginfo=meta)
        images.append(img)
        paths.append(str(path))

    status = (f"Done. {len(images)} image(s) saved in the 'outputs' folder.\n"
              f"Seed used: {seed}  (type this same number next time to "
              f"recreate these exact images)")
    return images, status

# ----------------------------------------------------------------------------
# Preset handling
# ----------------------------------------------------------------------------
def apply_preset(name):
    p = PRESETS.get(name)
    if not p:
        return [gr.update()] * 6
    return [
        gr.update(value=p.get("bag_type", BAG_TYPES[0])),
        gr.update(value=p.get("color", "")),
        gr.update(value=p.get("location", list(LOCATIONS)[0])),
        gr.update(value=p.get("lighting", list(LIGHTING)[0])),
        gr.update(value=p.get("style", list(STYLES)[0])),
        gr.update(value=p.get("people", list(PEOPLE)[0])),
    ]

# ----------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------
CSS = """
.gradio-container {max-width: 980px !important; margin: auto;}
#go-btn {height: 64px; font-size: 22px; font-weight: 700;}
#status-box textarea {font-size: 16px;}
footer {display: none !important;}
"""

with gr.Blocks(css=CSS, title="Travel Bag Co. — AI Image Studio",
               theme=gr.themes.Soft(primary_hue="orange")) as demo:

    gr.Markdown(
        "# 🧳 Travel Bag Co. — AI Image Studio\n"
        "Pick your options below, then press the big orange button. "
        "Images appear on the right and are also saved in the **outputs** folder."
    )

    with gr.Row():
        with gr.Column(scale=1):
            preset = gr.Dropdown(list(PRESETS), value="— Start from scratch —",
                                 label="1. Campaign preset (optional shortcut)")
            bag_type = gr.Dropdown(BAG_TYPES, value="Backpack",
                                   label="2. What kind of bag?")
            color = gr.Textbox(label="3. Bag color (plain words are fine)",
                               placeholder="e.g. midnight navy, sand beige")
            location = gr.Dropdown(list(LOCATIONS),
                                   value="Photo studio (clean background)",
                                   label="4. Where is the photo taken?")
            lighting = gr.Dropdown(list(LIGHTING), value="Soft studio light",
                                   label="5. Lighting")
            style = gr.Dropdown(list(STYLES), value="Product catalog (clean)",
                                label="6. Photo style")
            people = gr.Dropdown(list(PEOPLE), value="No people — bag only",
                                 label="7. People in the shot?")

            with gr.Accordion("More options (you can ignore these)", open=False):
                extra = gr.Textbox(label="Extra details (optional)",
                                   placeholder="e.g. leather straps, brass zippers")
                aspect = gr.Dropdown(list(ASPECTS),
                                     value="Square 1:1  (Instagram post)",
                                     label="Image shape")
                count = gr.Slider(1, 4, value=2, step=1,
                                  label="How many variations?")
                seed_text = gr.Textbox(label="Seed (leave blank for new ideas; "
                                             "enter a number to repeat a result)")
                model_label = gr.Dropdown(list(MODELS),
                                          value=list(MODELS)[0],
                                          label="Model")

            go = gr.Button("✨  Create my images", elem_id="go-btn",
                           variant="primary")

        with gr.Column(scale=1):
            gallery = gr.Gallery(label="Your images", columns=2, height=560,
                                 object_fit="contain")
            status = gr.Textbox(label="Status", elem_id="status-box",
                                interactive=False, lines=3,
                                value="Ready when you are. The very first run "
                                      "downloads the model (one-time wait — "
                                      "watch the Terminal window).")

    preset.change(apply_preset, inputs=preset,
                  outputs=[bag_type, color, location, lighting, style, people])
    go.click(generate,
             inputs=[model_label, bag_type, color, location, lighting, style,
                     people, extra, aspect, count, seed_text],
             outputs=[gallery, status])

if __name__ == "__main__":
    demo.launch(inbrowser=True, show_api=False)
