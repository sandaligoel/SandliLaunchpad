const API_BASE = (import.meta.env.VITE_AFFINE_API_BASE ?? "").replace(/\/$/, "");

export interface ImageAnalysis {
  subject: string;
  scene: string;
  key_details: string[];
  brand_or_product_cues: string;
  motion_opportunities: string;
  camera_suggestion: string;
  tone: string;
  video_prompt: string;
}

export type MediaJobStatus =
  | "queued"
  | "analyzing"
  | "generating_video"
  | "completed"
  | "analysis_only"
  | "failed";

export interface MediaJob {
  id: string;
  status: MediaJobStatus;
  analysis: ImageAnalysis | null;
  video_prompt: string | null;
  error: string | null;
  video_url: string | null;
  seconds: number;
  size: string;
}

export function mediaVideoUrl(job: MediaJob): string | null {
  if (!job.video_url) return null;
  if (job.video_url.startsWith("http")) return job.video_url;
  return `${API_BASE}${job.video_url}`;
}

export async function startImageToVideo(params: {
  file: File;
  userHint?: string;
  seconds?: number;
  size?: string;
}): Promise<MediaJob> {
  const form = new FormData();
  form.append("file", params.file);
  form.append("user_hint", params.userHint ?? "");
  form.append("seconds", String(params.seconds ?? 8));
  form.append("size", params.size ?? "1280x720");

  const res = await fetch(`${API_BASE}/api/media/image-to-video`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      (err as { detail?: string }).detail ?? `Upload failed (${res.status})`,
    );
  }
  return res.json() as Promise<MediaJob>;
}

export async function getMediaJob(jobId: string): Promise<MediaJob> {
  const res = await fetch(`${API_BASE}/api/media/jobs/${jobId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      (err as { detail?: string }).detail ?? `Job fetch failed (${res.status})`,
    );
  }
  return res.json() as Promise<MediaJob>;
}
