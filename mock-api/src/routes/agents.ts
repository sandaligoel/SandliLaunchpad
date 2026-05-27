import { Router } from "express";
import { AGENT_REGISTRY } from "../data/mock.js";

const router = Router();

router.get("/", (_req, res) => {
  res.json(AGENT_REGISTRY);
});

router.get("/:type", (req, res) => {
  const agent = AGENT_REGISTRY.find((a) => a.type === req.params.type);
  if (!agent) return res.status(404).json({ error: "Agent type not found" });
  res.json(agent);
});

export default router;
