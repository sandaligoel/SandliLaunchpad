"""Upload image → vision analysis → Sora image-to-video (when configured)."""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any

from openai import AzureOpenAI
from PIL import Image

from config import Settings
from schemas.media_job import ImageAnalysis, MediaJobResponse, MediaJobStatus
from services.llm import load_prompt, make_client, strip_json_fences

logger = logging.getLogger(__name__)

JOBS_DIR = Path(__file__).resolve().parent.parent / "data" / "media_jobs"
MAX_IMAGE_BYTES = 12 * 1024 * 1024
ALLOWED_SECONDS = {4, 8, 12}
ALLOWED_SIZES = {"1280x720", "720x1280"}
POLL_INTERVAL_S = 5
MAX_POLL_S = 600


def _video_deployment(settings: Settings) -> str:
    return os.getenv("AZURE_OPENAI_VIDEO_DEPLOYMENT", "").strip()


def _job_path(job_id: str) -> Path:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    return JOBS_DIR / f"{job_id}.json"


def _video_path(job_id: str) -> Path:
    return JOBS_DIR / f"{job_id}.mp4"


def _load_job(job_id: str) -> dict[str, Any]:
    path = _job_path(job_id)
    if not path.is_file():
        raise FileNotFoundError(f"Job not found: {job_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def _save_job(job: dict[str, Any]) -> None:
    _job_path(job["id"]).write_text(
        json.dumps(job, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _to_response(job: dict[str, Any]) -> MediaJobResponse:
    analysis_raw = job.get("analysis")
    analysis = ImageAnalysis.model_validate(analysis_raw) if analysis_raw else None
    video_url = f"/api/media/jobs/{job['id']}/video" if job.get("video_ready") else None
    return MediaJobResponse(
        id=job["id"],
        status=job["status"],
        analysis=analysis,
        video_prompt=job.get("video_prompt"),
        error=job.get("error"),
        video_url=video_url,
        seconds=job.get("seconds", 8),
        size=job.get("size", "1280x720"),
    )


def get_job(job_id: str) -> MediaJobResponse:
    return _to_response(_load_job(job_id))


def _resize_for_video(image_bytes: bytes, size: str) -> bytes:
    width, height = (int(x) for x in size.split("x"))
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    elif img.mode == "RGBA":
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    img = img.resize((width, height), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def _analyze_image(
    settings: Settings,
    image_bytes: bytes,
    user_hint: str,
) -> ImageAnalysis:
    client = make_client(settings)
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    system = load_prompt("image_video_analysis.txt")
    user_parts = [
        {
            "type": "text",
            "text": (
                "Analyze this image for a short marketing video."
                + (f"\nUser direction: {user_hint}" if user_hint.strip() else "")
            ),
        },
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
        },
    ]
    response = client.chat.completions.create(
        model=settings.azure_openai_chat_deployment,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_parts},
        ],
        temperature=0.25,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or "{}"
    parsed = json.loads(strip_json_fences(content))
    return ImageAnalysis.model_validate(parsed)


def _poll_sora_job(
    client: AzureOpenAI,
    video_id: str,
    deployment: str,
) -> None:
    deadline = time.time() + MAX_POLL_S
    while time.time() < deadline:
        status_obj = client.videos.retrieve(video_id)
        status = getattr(status_obj, "status", None) or ""
        if status == "completed":
            return
        if status in ("failed", "cancelled"):
            err = getattr(status_obj, "error", None)
            msg = str(err) if err else status
            raise RuntimeError(f"Video generation failed: {msg}")
        time.sleep(POLL_INTERVAL_S)
    raise TimeoutError("Video generation timed out")


def _generate_video_sora(
    settings: Settings,
    image_bytes: bytes,
    prompt: str,
    *,
    size: str,
    seconds: int,
    job_id: str,
) -> Path:
    deployment = _video_deployment(settings)
    if not deployment:
        raise ValueError(
            "Video generation is not configured. Set AZURE_OPENAI_VIDEO_DEPLOYMENT "
            "to your Azure Sora deployment name (e.g. sora-2)."
        )

    client = make_client(settings)
    if not hasattr(client, "videos"):
        raise RuntimeError(
            "OpenAI SDK does not support videos API. Run: pip install -U openai"
        )

    prepared = _resize_for_video(image_bytes, size)
    ref = io.BytesIO(prepared)
    ref.name = "reference.jpg"

    video = client.videos.create(
        model=deployment,
        prompt=prompt[:15000],
        size=size,
        seconds=str(seconds),
        input_reference=ref,
    )
    video_id = video.id
    logger.info("Sora job started: %s", video_id)
    _poll_sora_job(client, video_id, deployment)

    out = _video_path(job_id)
    content = client.videos.download_content(video_id)
    data = content.read() if hasattr(content, "read") else bytes(content)
    out.write_bytes(data)
    return out


def run_image_to_video_job(
    job_id: str,
    image_bytes: bytes,
    settings: Settings,
    *,
    user_hint: str = "",
    seconds: int = 8,
    size: str = "1280x720",
) -> MediaJobResponse:
    job = _load_job(job_id)
    try:
        job["status"] = "analyzing"
        _save_job(job)

        analysis = _analyze_image(settings, image_bytes, user_hint)
        prompt = (analysis.video_prompt or "").strip()
        if not prompt:
            prompt = (
                f"Cinematic shot of {analysis.subject}. {analysis.motion_opportunities}. "
                f"{analysis.camera_suggestion}. {analysis.tone}."
            )

        job["analysis"] = analysis.model_dump()
        job["video_prompt"] = prompt
        job["status"] = "generating_video"
        _save_job(job)

        deployment = _video_deployment(settings)
        if not deployment:
            job["status"] = "analysis_only"
            job["error"] = (
                "Analysis complete. Add AZURE_OPENAI_VIDEO_DEPLOYMENT to backend/.env "
                "to enable Sora video rendering."
            )
            _save_job(job)
            return _to_response(job)

        _generate_video_sora(
            settings,
            image_bytes,
            prompt,
            size=size,
            seconds=seconds,
            job_id=job_id,
        )
        job["status"] = "completed"
        job["video_ready"] = True
        job["error"] = None
        _save_job(job)
        return _to_response(job)
    except Exception as exc:
        logger.exception("Image-to-video job %s failed", job_id)
        job["status"] = "failed"
        job["error"] = str(exc)
        if job.get("analysis"):
            job["status"] = "analysis_only"
        _save_job(job)
        return _to_response(job)


def create_image_to_video_job(
    image_bytes: bytes,
    settings: Settings,
    *,
    user_hint: str = "",
    seconds: int = 8,
    size: str = "1280x720",
) -> MediaJobResponse:
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ValueError("Image must be under 12 MB")
    if seconds not in ALLOWED_SECONDS:
        seconds = 8
    if size not in ALLOWED_SIZES:
        size = "1280x720"

    job_id = str(uuid.uuid4())
    job: dict[str, Any] = {
        "id": job_id,
        "status": "queued",
        "seconds": seconds,
        "size": size,
        "user_hint": user_hint,
        "video_ready": False,
    }
    _save_job(job)
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    (_video_path(job_id).with_suffix(".upload.jpg")).write_bytes(image_bytes)
    return _to_response(job)


def get_job_video_path(job_id: str) -> Path:
    return _video_path(job_id)


def get_job_image_bytes(job_id: str) -> bytes:
    path = _video_path(job_id).with_suffix(".upload.jpg")
    if not path.is_file():
        raise FileNotFoundError("Source image not found for job")
    return path.read_bytes()
