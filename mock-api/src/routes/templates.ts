import { Router } from "express";
import { TEMPLATES } from "../data/mock.js";

const router = Router();

router.get("/", (_req, res) => {
  res.json(TEMPLATES);
});

router.get("/:id", (req, res) => {
  const tpl = TEMPLATES.find((t) => t.id === req.params.id);
  if (!tpl) return res.status(404).json({ error: "Template not found" });
  res.json(tpl);
});

export default router;
