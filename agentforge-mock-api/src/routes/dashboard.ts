import { Router } from "express";
import { RUNS, RUNS_OVER_TIME, AGENT_USAGE, WORKFLOWS } from "../data/mock.js";

const router = Router();

router.get("/stats", (_req, res) => {
  const totalWorkflows = WORKFLOWS.length;
  const activeAgents = 147;
  const runsToday = RUNS.filter((r) => {
    const today = new Date();
    const runDate = new Date(r.startedAt);
    return runDate.toDateString() === today.toDateString();
  }).length || 412;
  const avgLatency =
    RUNS.reduce((sum, r) => sum + r.durationMs, 0) / RUNS.length / 1000;

  res.json({
    totalWorkflows,
    activeAgents,
    runsToday,
    avgLatency: `${avgLatency.toFixed(2)}s`,
  });
});

router.get("/runs-over-time", (_req, res) => {
  res.json(RUNS_OVER_TIME);
});

router.get("/agent-usage", (_req, res) => {
  res.json(AGENT_USAGE);
});

router.get("/recent-runs", (_req, res) => {
  res.json(RUNS.slice(0, 6));
});

router.get("/top-workflows", (_req, res) => {
  const sorted = [...WORKFLOWS].sort((a, b) => b.successRate - a.successRate);
  res.json(sorted.slice(0, 5));
});

export default router;
