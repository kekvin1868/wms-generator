"""Video server: holds the fal key, checks invite keys + monthly quota, queues clips on fal.

Run from the repo root:  uvicorn video_server.main:app
See docs/video-plan.md §4.
"""

from __future__ import annotations

import datetime
import hashlib
import os
import uuid

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from backend.constants import BAG_TYPES
from backend.prompts import build_video_prompt

FAL_KEY = os.environ["FAL_KEY"]
SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
FAL_MODEL = os.environ.get("FAL_MODEL", "fal-ai/wan/v2.2-a14b/text-to-video")

# Pinned here, never taken from the request, so a modified client can't order pricier clips.
# ponytail: input names differ per fal model; confirm against the chosen model's schema (plan Phase 0).
VIDEO_INPUT = {"resolution": "1080p", "duration": 10}

app = FastAPI(title="Travel Bag Co. — Video Server")
http = httpx.AsyncClient(timeout=30)


class VideoRequest(BaseModel):
    bag_type: str
    color: str = Field(default="", max_length=40)
    location: str
    lighting: str
    style: str
    people: str
    motion: str


# ---------- Supabase (PostgREST) ----------
def _sb_headers() -> dict[str, str]:
    return {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}


async def rpc(fn: str, **args) -> httpx.Response:
    return await http.post(f"{SUPABASE_URL}/rest/v1/rpc/{fn}", json=args, headers=_sb_headers())


async def patch_job(job_id: str, **fields) -> None:
    r = await http.patch(
        f"{SUPABASE_URL}/rest/v1/video_jobs",
        params={"id": f"eq.{job_id}"},
        json=fields,
        headers=_sb_headers(),
    )
    r.raise_for_status()


async def finish(job_id: str, status: str, **fields) -> None:
    now = datetime.datetime.now(datetime.UTC).isoformat()
    await patch_job(job_id, status=status, finished_at=now, **fields)


# ---------- auth ----------
def key_hash(x_invite_key: str = Header(...)) -> str:
    return hashlib.sha256(x_invite_key.encode()).hexdigest()


# ---------- routes ----------
@app.get("/me")
async def me(kh: str = Depends(key_hash)):
    r = await rpc("quota_status", p_key_hash=kh)
    r.raise_for_status()
    rows = r.json()
    if not rows:
        raise HTTPException(401, "Invalid invite key")
    row = rows[0]
    return {**row, "left": max(0, row["quota"] - row["used"])}


@app.post("/jobs")
async def create_job(req: VideoRequest, kh: str = Depends(key_hash)):
    if req.bag_type not in BAG_TYPES:
        raise HTTPException(422, f"Unknown bag_type: {req.bag_type}")
    try:
        prompt = build_video_prompt(
            req.bag_type, req.color, req.location, req.lighting, req.style, req.people, req.motion
        )
    except KeyError as exc:
        raise HTTPException(422, f"Unknown option: {exc.args[0]}") from None

    r = await rpc("reserve_clip", p_key_hash=kh, p_prompt=prompt)
    if r.status_code >= 400:
        msg = r.json().get("message", "")
        if msg == "invalid_key":
            raise HTTPException(401, "Invalid invite key")
        if msg == "quota_exceeded":
            raise HTTPException(429, "Monthly video quota used up")
        r.raise_for_status()
    job_id = r.json()

    try:
        sub = await http.post(
            f"https://queue.fal.run/{FAL_MODEL}",
            json={"prompt": prompt, **VIDEO_INPUT},
            headers={"Authorization": f"Key {FAL_KEY}"},
        )
        sub.raise_for_status()
        q = sub.json()
    except httpx.HTTPError as exc:
        await finish(job_id, "failed", error=f"fal submit failed: {exc}")  # refunds the slot
        raise HTTPException(502, "Video service unavailable, clip not charged") from None

    await patch_job(job_id, status_url=q["status_url"], response_url=q["response_url"])
    return {"job_id": job_id, "prompt": prompt}


@app.get("/jobs/{job_id}")
async def get_job(job_id: uuid.UUID, kh: str = Depends(key_hash)):
    r = await rpc("get_job", p_key_hash=kh, p_job=str(job_id))
    r.raise_for_status()
    rows = r.json()
    if not rows:
        raise HTTPException(404, "Unknown job")
    job = rows[0]
    out = {"job_id": job["id"], "prompt": job["prompt"]}

    if job["status"] == "done":
        return {**out, "status": "done", "video_url": job["video_url"]}
    if job["status"] == "failed":
        return {**out, "status": "failed", "error": job["error"]}
    if not job["status_url"]:
        return {**out, "status": "queued"}  # reserved, submit still in flight

    fal_auth = {"Authorization": f"Key {FAL_KEY}"}
    try:
        st = await http.get(job["status_url"], headers=fal_auth)
    except httpx.HTTPError:
        return {**out, "status": "running"}  # transient; try again next poll
    if st.status_code >= 500 or st.status_code == 429:
        return {**out, "status": "running"}
    if st.status_code >= 400:  # fal no longer knows this request
        await finish(job["id"], "failed", error=f"fal status {st.status_code}")
        return {**out, "status": "failed", "error": "Video job was lost, clip not charged"}

    fal_status = st.json().get("status")
    if fal_status == "IN_QUEUE":
        return {**out, "status": "queued"}
    if fal_status != "COMPLETED":
        return {**out, "status": "running"}

    res = await http.get(job["response_url"], headers=fal_auth)
    video_url = (res.json().get("video") or {}).get("url") if res.status_code == 200 else None
    if not video_url:
        await finish(job["id"], "failed", error=f"fal result {res.status_code}: {res.text[:300]}")
        return {**out, "status": "failed", "error": "Video generation failed, clip not charged"}

    await finish(job["id"], "done", video_url=video_url)
    return {**out, "status": "done", "video_url": video_url}
