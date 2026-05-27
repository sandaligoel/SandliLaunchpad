import express from "express";
import cors from "cors";
import agentsRouter from "./routes/agents.js";
import workflowsRouter from "./routes/workflows.js";
import runsRouter from "./routes/runs.js";
import credentialsRouter from "./routes/credentials.js";
import templatesRouter from "./routes/templates.js";
import dashboardRouter from "./routes/dashboard.js";

const app = express();
const PORT = process.env.PORT ?? 3001;

app.use(cors());
app.use(express.json());

app.use("/api/agents", agentsRouter);
app.use("/api/workflows", workflowsRouter);
app.use("/api/runs", runsRouter);
app.use("/api/credentials", credentialsRouter);
app.use("/api/templates", templatesRouter);
app.use("/api/dashboard", dashboardRouter);

app.get("/api/health", (_req, res) => {
  res.json({ status: "ok", timestamp: new Date().toISOString() });
});

app.listen(PORT, () => {
  console.log(`Backend running on http://localhost:${PORT}`);
});
