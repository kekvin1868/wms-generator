"""Pydantic models for the FastAPI surface."""

from typing import Literal

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    model_label: str
    bag_type: str
    color: str = ""
    location: str
    lighting: str
    style: str
    people: str
    extra: str = ""
    aspect: str
    count: int = Field(default=2, ge=1, le=4)
    seed_text: str = ""


class GeneratedImage(BaseModel):
    filename: str
    url: str
    seed: int


class ProgressEvent(BaseModel):
    type: Literal["progress"] = "progress"
    step: int
    total: int
    percent: float
    desc: str


class DoneEvent(BaseModel):
    type: Literal["done"] = "done"
    images: list[GeneratedImage]
    seed_used: int
    prompt: str


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    message: str


class HistoryItem(BaseModel):
    filename: str
    url: str
    prompt: str | None = None
    seed: int | None = None
    model: str | None = None
    created_at: float
