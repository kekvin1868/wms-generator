"""FastAPI entry point for the Travel Bag Co. AI Image Studio."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from . import pipeline
from .constants import (
    ASPECTS,
    BAG_TYPES,
    LIGHTING,
    LOCATIONS,
    MODELS,
    OUTPUT_DIR,
    PEOPLE,
    STYLES,
)
from .presets import load_presets
from .schemas import GenerateRequest

app = FastAPI(title="Travel Bag Co. — AI Image Studio API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")


@app.get("/api/options")
def get_options():
    return {
        "models": list(MODELS.keys()),
        "aspects": list(ASPECTS.keys()),
        "bag_types": BAG_TYPES,
        "locations": list(LOCATIONS.keys()),
        "lighting": list(LIGHTING.keys()),
        "styles": list(STYLES.keys()),
        "people": list(PEOPLE.keys()),
    }


@app.get("/api/presets")
def get_presets():
    presets = load_presets()
    return [
        {"name": name, **(data or {})} for name, data in presets.items()
    ]


@app.post("/api/generate")
def post_generate(req: GenerateRequest):
    job_id = pipeline.submit_job(req)
    return {"job_id": job_id}


@app.get("/api/generate/{job_id}/stream")
async def stream_generate(job_id: str):
    req = pipeline.pop_job(job_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Unknown or already-consumed job_id")

    async def event_publisher():
        async for evt in pipeline.run(req):
            yield {"event": evt.type, "data": evt.model_dump_json()}

    return EventSourceResponse(event_publisher())


@app.get("/api/history")
def get_history():
    from .history import list_history

    return list_history()


@app.get("/api/health")
def health():
    return {"ok": True, "device": pipeline.DEVICE, "dtype": str(pipeline.DTYPE)}
