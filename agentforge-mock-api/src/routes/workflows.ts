import { Router } from "express";
import { WORKFLOWS } from "../data/mock.js";

const router = Router();

router.get("/", (_req, res) => {
  res.json(WORKFLOWS);
});

router.get("/:id", (req, res) => {
  const wf = WORKFLOWS.find((w) => w.id === req.params.id);
  if (!wf) return res.status(404).json({ error: "Workflow not found" });
  res.json(wf);
});

export default router;
