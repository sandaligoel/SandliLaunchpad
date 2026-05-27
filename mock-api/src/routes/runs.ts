import { Router } from "express";
import { RUNS } from "../data/mock.js";

const router = Router();

router.get("/", (req, res) => {
  const { status, q } = req.query;
  let filtered = RUNS;

  if (status && status !== "all") {
    filtered = filtered.filter((r) => r.status === status);
  }
  if (q && typeof q === "string") {
    const lower = q.toLowerCase();
    filtered = filtered.filter((r) => r.workflowName.toLowerCase().includes(lower));
  }

  res.json(filtered);
});

router.get("/:id", (req, res) => {
  const run = RUNS.find((r) => r.id === req.params.id);
  if (!run) return res.status(404).json({ error: "Run not found" });
  res.json(run);
});

export default router;
