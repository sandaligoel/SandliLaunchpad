"""Image → analysis → video generation job models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

MediaJobStatus = Literal[
    "queued",
    "analyzing",
    "generating_video",
    "completed",
    "analysis_only",
    "failed",
]


class ImageAnalysis(BaseModel):
    subject: str = ""
    scene: str = ""
    key_details: list[str] = Field(default_factory=list)
    brand_or_product_cues: str = ""
    motion_opportunities: str = ""
    camera_suggestion: str = ""
    tone: str = ""
    video_prompt: str = ""


class MediaJobResponse(BaseModel):
    id: str
    status: MediaJobStatus
    analysis: ImageAnalysis | None = None
    video_prompt: str | None = None
    error: str | None = None
    video_url: str | None = None
    seconds: int = 8
    size: str = "1280x720"
