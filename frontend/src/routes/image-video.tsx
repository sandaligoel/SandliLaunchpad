import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Topbar } from "@/components/layout/Topbar";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import {
  getMediaJob,
  mediaVideoUrl,
  startImageToVideo,
  type MediaJob,
} from "@/api/affine/media";

export const Route = createFileRoute("/image-video")({
  head: () => ({
    meta: [{ title: "Image to Video — AgentForge | Affine" }],
  }),
  component: ImageVideoPage,
});

const POLL_MS = 3000;

function ImageVideoPage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [hint, setHint] = useState("");
  const [seconds, setSeconds] = useState(8);
  const [size, setSize] = useState("1280x720");
  const [job, setJob] = useState<MediaJob | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPoll = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => () => stopPoll(), [stopPoll]);

  useEffect(() => {
    if (!job) return;
    const terminal = ["completed", "analysis_only", "failed"].includes(job.status);
    if (terminal) {
      stopPoll();
      setLoading(false);
      return;
    }
    stopPoll();
    pollRef.current = setInterval(async () => {
      try {
        const updated = await getMediaJob(job.id);
        setJob(updated);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Poll failed");
        stopPoll();
        setLoading(false);
      }
    }, POLL_MS);
    return () => stopPoll();
  }, [job?.id, job?.status, stopPoll]);

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setJob(null);
    setError(null);
  };

  const handleGenerate = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setJob(null);
    try {
      const created = await startImageToVideo({
        file,
        userHint: hint,
        seconds,
        size,
      });
      setJob(created);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start");
      setLoading(false);
    }
  };

  const videoSrc = job ? mediaVideoUrl(job) : null;

  return (
    <AppShell>
      <Topbar
        title="Image to Video"
        subtitle="Upload → vision analysis → Sora render"
      />
      <div className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto w-full space-y-6">
        <Card className="p-5 space-y-4">
          <div>
            <h2 className="text-lg font-semibold">Upload an image</h2>
            <p className="text-sm text-muted-foreground mt-1">
              We analyze the frame with Azure OpenAI vision, then generate a short
              MP4 with Azure Sora when{" "}
              <code className="text-xs">AZURE_OPENAI_VIDEO_DEPLOYMENT</code> is set
              in backend/.env.
            </p>
          </div>
          <input
            type="file"
            accept="image/*"
            onChange={onFileChange}
            className="text-sm"
          />
          {preview ? (
            <img
              src={preview}
              alt="Upload preview"
              className="max-h-64 rounded-lg border border-border object-contain"
            />
          ) : null}
          <Textarea
            placeholder="Optional direction (e.g. slow cinematic push-in, premium product ad)"
            value={hint}
            onChange={(e) => setHint(e.target.value)}
            rows={2}
          />
          <div className="flex flex-wrap gap-4 text-sm">
            <label className="flex items-center gap-2">
              Duration
              <select
                value={seconds}
                onChange={(e) => setSeconds(Number(e.target.value))}
                className="rounded border border-border bg-background px-2 py-1"
              >
                <option value={4}>4s</option>
                <option value={8}>8s</option>
                <option value={12}>12s</option>
              </select>
            </label>
            <label className="flex items-center gap-2">
              Aspect
              <select
                value={size}
                onChange={(e) => setSize(e.target.value)}
                className="rounded border border-border bg-background px-2 py-1"
              >
                <option value="1280x720">Landscape 1280×720</option>
                <option value="720x1280">Portrait 720×1280</option>
              </select>
            </label>
          </div>
          <Button onClick={handleGenerate} disabled={!file || loading}>
            {loading ? "Processing…" : "Analyze & generate video"}
          </Button>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
        </Card>

        {job ? (
          <Card className="p-5 space-y-4">
            <p className="text-sm">
              Status:{" "}
              <span className="font-medium text-primary">{job.status}</span>
            </p>
            {job.error ? (
              <p className="text-sm text-amber-400">{job.error}</p>
            ) : null}
            {job.analysis ? (
              <div className="space-y-2 text-sm">
                <p>
                  <span className="text-muted-foreground">Subject:</span>{" "}
                  {job.analysis.subject}
                </p>
                <p>
                  <span className="text-muted-foreground">Scene:</span>{" "}
                  {job.analysis.scene}
                </p>
                <p>
                  <span className="text-muted-foreground">Motion:</span>{" "}
                  {job.analysis.motion_opportunities}
                </p>
                {job.analysis.key_details?.length ? (
                  <ul className="list-disc pl-5 text-muted-foreground">
                    {job.analysis.key_details.map((d) => (
                      <li key={d}>{d}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ) : null}
            {job.video_prompt ? (
              <div>
                <p className="text-xs font-semibold uppercase text-muted-foreground mb-1">
                  Video prompt
                </p>
                <p className="text-sm whitespace-pre-wrap">{job.video_prompt}</p>
              </div>
            ) : null}
            {videoSrc ? (
              <video
                src={videoSrc}
                controls
                className="w-full max-h-[480px] rounded-lg border border-border bg-black"
              />
            ) : null}
          </Card>
        ) : null}
      </div>
    </AppShell>
  );
}
