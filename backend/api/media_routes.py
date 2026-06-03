"""Image upload → analysis → video generation API."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from config import get_settings
from schemas.media_job import MediaJobResponse
from services.image_video_service import (
    create_image_to_video_job,
    get_job,
    get_job_image_bytes,
    run_image_to_video_job,
    get_job_video_path,
)

media_router = APIRouter(prefix="/api/media", tags=["media"])


def _process_job(job_id: str, user_hint: str, seconds: int, size: str) -> None:
    settings = get_settings()
    image_bytes = get_job_image_bytes(job_id)
    run_image_to_video_job(
        job_id,
        image_bytes,
        settings,
        user_hint=user_hint,
        seconds=seconds,
        size=size,
    )


@media_router.post("/image-to-video", response_model=MediaJobResponse)
async def start_image_to_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_hint: str = Form(""),
    seconds: int = Form(8),
    size: str = Form("1280x720"),
) -> MediaJobResponse:
    """Upload an image; analyze it and generate a short video (Azure Sora when configured)."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Upload must be an image file")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    settings = get_settings()
    try:
        job = await run_in_threadpool(
            create_image_to_video_job,
            raw,
            settings,
            user_hint=user_hint.strip(),
            seconds=seconds,
            size=size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    background_tasks.add_task(
        _process_job,
        job.id,
        user_hint.strip(),
        seconds,
        size,
    )
    return job


@media_router.get("/jobs/{job_id}", response_model=MediaJobResponse)
async def read_job(job_id: str) -> MediaJobResponse:
    try:
        return await run_in_threadpool(get_job, job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@media_router.get("/jobs/{job_id}/video")
async def download_job_video(job_id: str) -> FileResponse:
    path = get_job_video_path(job_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Video not ready yet")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=f"{job_id}.mp4",
    )
