"""Image generation pipeline. Lifted from app.py and adapted for async streaming."""

from __future__ import annotations

import asyncio
import base64
import binascii
import datetime
import os
import re
import uuid
from io import BytesIO
from typing import AsyncIterator

import torch
from PIL import Image, ImageOps, PngImagePlugin

from .constants import (
    ALLOWED_REFERENCE_IMAGE_FORMATS,
    ASPECTS,
    DEFAULT_NEGATIVE,
    LIGHTING,
    LOCATIONS,
    MAX_REFERENCE_IMAGE_BYTES,
    MODELS,
    OUTPUT_DIR,
    PEOPLE,
    REFS_DIR,
    STYLES,
)
from .schemas import DoneEvent, ErrorEvent, GeneratedImage, GenerateRequest, ProgressEvent

# ---------- device ----------
if torch.backends.mps.is_available():
    DEVICE, DTYPE = "mps", torch.float16
elif torch.cuda.is_available():
    DEVICE, DTYPE = "cuda", torch.float16
else:
    DEVICE, DTYPE = "cpu", torch.float32

_PIPES: dict[str, object] = {}
_LOCK = asyncio.Lock()
_JOBS: dict[str, GenerateRequest] = {}


def submit_job(req: GenerateRequest) -> str:
    job_id = uuid.uuid4().hex
    _JOBS[job_id] = req
    return job_id


def pop_job(job_id: str) -> GenerateRequest | None:
    return _JOBS.pop(job_id, None)


def safe_name(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:30]


def decode_reference_image(data: str) -> Image.Image:
    """Decode a (optionally data-URL-prefixed) base64 image and validate it."""
    raw_b64 = data.split(",", 1)[1] if data.strip().startswith("data:") else data
    try:
        raw = base64.b64decode(raw_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Reference image is not valid base64") from exc

    if len(raw) > MAX_REFERENCE_IMAGE_BYTES:
        raise ValueError("Reference image exceeds the 10 MB limit")

    try:
        img = Image.open(BytesIO(raw))
        img.load()
    except Exception as exc:
        raise ValueError("Reference image could not be decoded") from exc

    if img.format not in ALLOWED_REFERENCE_IMAGE_FORMATS:
        raise ValueError(f"Unsupported reference image format: {img.format}")

    return img.convert("RGB")


def fit_reference_image(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Center-crop + resize the reference image to match the target aspect."""
    return ImageOps.fit(img, size, method=Image.LANCZOS, centering=(0.5, 0.5))


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


# Lightning ships 1/2/4/8-step distilled checkpoints. img2img needs more headroom
# than 4 steps (strength < 1 leaves too few effective denoising steps), so the
# img2img path uses the 8-step checkpoint instead.
LIGHTNING_STEPS = {False: 4, True: 8}


def _load_pipeline(model_key: str, img2img: bool = False):
    cache_key = f"{model_key}_img2img" if img2img else model_key
    if cache_key in _PIPES:
        return _PIPES[cache_key]

    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")

    if model_key == "lightning":
        from diffusers import (
            EulerDiscreteScheduler,
            StableDiffusionXLImg2ImgPipeline,
            StableDiffusionXLPipeline,
        )
        from huggingface_hub import hf_hub_download

        n_steps = LIGHTNING_STEPS[img2img]
        ckpt = hf_hub_download(
            "ByteDance/SDXL-Lightning",
            f"sdxl_lightning_{n_steps}step.safetensors",
            token=hf_token,
        )
        pipe_cls = StableDiffusionXLImg2ImgPipeline if img2img else StableDiffusionXLPipeline
        pipe = pipe_cls.from_single_file(ckpt, torch_dtype=DTYPE)
        pipe.scheduler = EulerDiscreteScheduler.from_config(
            pipe.scheduler.config, timestep_spacing="trailing"
        )
    elif img2img:  # sd15 img2img — share weights with the cached txt2img pipe
        from diffusers import AutoPipelineForImage2Image

        pipe = AutoPipelineForImage2Image.from_pipe(_load_pipeline("sd15"))
    else:  # sd15
        from diffusers import StableDiffusionPipeline

        pipe = StableDiffusionPipeline.from_pretrained(
            "stable-diffusion-v1-5/stable-diffusion-v1-5",
            torch_dtype=DTYPE,
            safety_checker=None,
            requires_safety_checker=False,
            token=hf_token,
        )

    pipe = pipe.to(DEVICE)
    pipe.enable_attention_slicing()
    _PIPES[cache_key] = pipe
    return pipe


async def run(req: GenerateRequest) -> AsyncIterator[ProgressEvent | DoneEvent | ErrorEvent]:
    """Yield ProgressEvent updates then a single DoneEvent or ErrorEvent."""
    async with _LOCK:
        try:
            if req.model_label not in MODELS:
                yield ErrorEvent(message=f"Unknown model: {req.model_label}")
                return
            model_key = MODELS[req.model_label]

            ref_img: Image.Image | None = None
            if req.reference_image:
                try:
                    ref_img = decode_reference_image(req.reference_image)
                except ValueError as exc:
                    yield ErrorEvent(message=str(exc))
                    return

            yield ProgressEvent(
                step=0,
                total=int(req.count),
                percent=0.02,
                desc="Loading model (first run downloads ~7 GB — watch the terminal)…",
            )

            loop = asyncio.get_running_loop()
            pipe = await loop.run_in_executor(
                None, _load_pipeline, model_key, ref_img is not None
            )

            w, h = ASPECTS[req.aspect]
            if model_key == "sd15":
                w = max(512, w // 2 // 8 * 8)
                h = max(512, h // 2 // 8 * 8)

            ref_fname: str | None = None
            if ref_img is not None:
                ref_img = fit_reference_image(ref_img, (w, h))
                ref_fname = f"ref_{uuid.uuid4().hex}.png"
                ref_img.save(REFS_DIR / ref_fname)

            prompt = build_prompt(
                req.bag_type,
                req.color,
                req.location,
                req.lighting,
                req.style,
                req.people,
                req.extra,
            )

            try:
                seed = int(req.seed_text)
            except (TypeError, ValueError):
                seed = torch.seed() % (2**32)

            images: list[GeneratedImage] = []
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            total = int(req.count)

            for i in range(total):
                yield ProgressEvent(
                    step=i + 1,
                    total=total,
                    percent=(i + 1) / (total + 1),
                    desc=f"Creating image {i + 1} of {total}…",
                )
                gen = torch.Generator("cpu").manual_seed(seed + i)

                def _gen():
                    steps = LIGHTNING_STEPS[ref_img is not None] if model_key == "lightning" else 25
                    guidance = 0.0 if model_key == "lightning" else 7.0
                    kwargs = dict(
                        negative_prompt=DEFAULT_NEGATIVE,
                        num_inference_steps=steps,
                        guidance_scale=guidance,
                        generator=gen,
                    )
                    if ref_img is not None:
                        kwargs["image"] = ref_img
                        kwargs["strength"] = req.strength
                    else:
                        kwargs["width"] = w
                        kwargs["height"] = h
                    return pipe(prompt, **kwargs).images[0]

                img = await loop.run_in_executor(None, _gen)

                meta = PngImagePlugin.PngInfo()
                meta.add_text("prompt", prompt)
                meta.add_text("negative_prompt", DEFAULT_NEGATIVE)
                meta.add_text("seed", str(seed + i))
                meta.add_text("model", model_key)
                if ref_fname:
                    meta.add_text("reference_image", ref_fname)
                    meta.add_text("strength", str(req.strength))

                fname = (
                    f"{safe_name(req.bag_type)}_{safe_name(req.location)}_"
                    f"{safe_name(req.lighting)}_seed{seed + i}_{stamp}.png"
                )
                path = OUTPUT_DIR / fname
                img.save(path, pnginfo=meta)
                images.append(
                    GeneratedImage(
                        filename=fname, url=f"/outputs/{fname}", seed=seed + i
                    )
                )

            yield DoneEvent(images=images, seed_used=seed, prompt=prompt)

        except Exception as exc:  # noqa: BLE001
            yield ErrorEvent(message=f"{type(exc).__name__}: {exc}")
