"""Image generation pipeline. Lifted from app.py and adapted for async streaming."""

from __future__ import annotations

import asyncio
import datetime
import re
import uuid
from typing import AsyncIterator

import torch
from PIL import PngImagePlugin

from .constants import (
    ASPECTS,
    DEFAULT_NEGATIVE,
    LIGHTING,
    LOCATIONS,
    MODELS,
    OUTPUT_DIR,
    PEOPLE,
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


def _load_pipeline(model_key: str):
    if model_key in _PIPES:
        return _PIPES[model_key]

    if model_key == "lightning":
        from diffusers import StableDiffusionXLPipeline, EulerDiscreteScheduler
        from huggingface_hub import hf_hub_download

        ckpt = hf_hub_download(
            "ByteDance/SDXL-Lightning", "sdxl_lightning_4step.safetensors"
        )
        pipe = StableDiffusionXLPipeline.from_single_file(ckpt, torch_dtype=DTYPE)
        pipe.scheduler = EulerDiscreteScheduler.from_config(
            pipe.scheduler.config, timestep_spacing="trailing"
        )
    else:  # sd15
        from diffusers import StableDiffusionPipeline

        pipe = StableDiffusionPipeline.from_pretrained(
            "stable-diffusion-v1-5/stable-diffusion-v1-5",
            torch_dtype=DTYPE,
            safety_checker=None,
            requires_safety_checker=False,
        )

    pipe = pipe.to(DEVICE)
    pipe.enable_attention_slicing()
    _PIPES[model_key] = pipe
    return pipe


async def run(req: GenerateRequest) -> AsyncIterator[ProgressEvent | DoneEvent | ErrorEvent]:
    """Yield ProgressEvent updates then a single DoneEvent or ErrorEvent."""
    async with _LOCK:
        try:
            if req.model_label not in MODELS:
                yield ErrorEvent(message=f"Unknown model: {req.model_label}")
                return
            model_key = MODELS[req.model_label]

            yield ProgressEvent(
                step=0,
                total=int(req.count),
                percent=0.02,
                desc="Loading model (first run downloads ~7 GB — watch the terminal)…",
            )

            loop = asyncio.get_running_loop()
            pipe = await loop.run_in_executor(None, _load_pipeline, model_key)

            w, h = ASPECTS[req.aspect]
            if model_key == "sd15":
                w = max(512, w // 2 // 8 * 8)
                h = max(512, h // 2 // 8 * 8)

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
                    if model_key == "lightning":
                        return pipe(
                            prompt,
                            negative_prompt=DEFAULT_NEGATIVE,
                            num_inference_steps=4,
                            guidance_scale=0.0,
                            width=w,
                            height=h,
                            generator=gen,
                        ).images[0]
                    return pipe(
                        prompt,
                        negative_prompt=DEFAULT_NEGATIVE,
                        num_inference_steps=25,
                        guidance_scale=7.0,
                        width=w,
                        height=h,
                        generator=gen,
                    ).images[0]

                img = await loop.run_in_executor(None, _gen)

                meta = PngImagePlugin.PngInfo()
                meta.add_text("prompt", prompt)
                meta.add_text("negative_prompt", DEFAULT_NEGATIVE)
                meta.add_text("seed", str(seed + i))
                meta.add_text("model", model_key)

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
