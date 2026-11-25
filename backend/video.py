"""Local side of video: forward jobs to the shared video server, save finished clips to outputs/."""

from __future__ import annotations

import json
import os
import time
import uuid

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .constants import OUTPUT_DIR

MAX_VIDEO_BYTES = 200 * 1024 * 1024

router = APIRouter(prefix="/api/video")
http = httpx.AsyncClient(timeout=60)


class VideoForm(BaseModel):
    bag_type: str
    color: str = ""
    location: str
    lighting: str
    style: str
    people: str
    motion: str


async def _server(method: str, path: str, **kw) -> dict:
    base = os.environ.get("VIDEO_SERVER_URL", "").rstrip("/")
    key = os.environ.get("VIDEO_INVITE_KEY", "")
    if not base or not key:
        raise HTTPException(503, "Video not set up: add VIDEO_SERVER_URL and VIDEO_INVITE_KEY to backend/.env")
    try:
        r = await http.request(method, f"{base}{path}", headers={"X-Invite-Key": key}, **kw)
    except httpx.HTTPError:
        raise HTTPException(502, "Video server unreachable (it may be waking up, try again)") from None
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail", r.text)
        except ValueError:
            detail = r.text
        raise HTTPException(r.status_code, detail)
    return r.json()


async def _download(url: str, dest) -> None:
    tmp = dest.with_suffix(".part")
    size = 0
    async with http.stream("GET", url) as r:
        r.raise_for_status()
        with tmp.open("wb") as f:
            async for chunk in r.aiter_bytes():
                size += len(chunk)
                if size > MAX_VIDEO_BYTES:
                    tmp.unlink(missing_ok=True)
                    raise HTTPException(502, "Video file too large")
                f.write(chunk)
    tmp.rename(dest)


@router.get("/quota")
async def quota():
    return await _server("GET", "/me")


@router.post("")
async def submit(form: VideoForm):
    return await _server("POST", "/jobs", json=form.model_dump())


@router.get("/{job_id}")
async def status(job_id: uuid.UUID):
    job = await _server("GET", f"/jobs/{job_id}")
    if job["status"] != "done":
        return job

    mp4 = OUTPUT_DIR / f"video_{job_id}.mp4"
    if not mp4.exists():
        try:
            await _download(job["video_url"], mp4)
        except httpx.HTTPError:
            raise HTTPException(502, "Clip finished but download failed, try again") from None
        sidecar = {"prompt": job["prompt"], "kind": "video", "created_at": time.time()}
        mp4.with_suffix(".json").write_text(json.dumps(sidecar))
    return {**job, "url": f"/outputs/{mp4.name}", "filename": mp4.name}
