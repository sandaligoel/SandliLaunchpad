import { Router } from "express";
import { CREDENTIALS } from "../data/mock.js";

const router = Router();

router.get("/", (_req, res) => {
  res.json(CREDENTIALS);
});

router.get("/:id", (req, res) => {
  const cred = CREDENTIALS.find((c) => c.id === req.params.id);
  if (!cred) return res.status(404).json({ error: "Credential not found" });
  res.json(cred);
});

export default router;
