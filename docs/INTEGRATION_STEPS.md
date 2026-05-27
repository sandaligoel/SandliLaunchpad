# AFFINE ↔ AgentForge UI — integration steps

Work in `frontend/`. AFFINE API: `backend` on **8003**. Mock API: **3001**.

| Step | Status | What |
|------|--------|------|
| **1** | Done | Launchpad in nav + Dashboard entry → `/interview` wired to AFFINE (`/api/sessions`, `/health`) |
| **2** | Done | After `ready`, auto-open `/builder?sessionId=…`; palette shows **Reuse** vs **Build**; canvas from architecture plan |
| 3 | Pending | Builder: load `POST /architecture`, render AFFINE graph + validation |
| 4 | Pending | Agent Library: optional link to `spec.catalog_hints` / catalog index |
| 5 | Pending | Retire or archive `launchpad-ui/` |

## Step 1 — verify

1. Terminal: `uvicorn` on **8003** (mock API on 3001 optional for other pages).
2. `cd frontend && npm run dev` → http://localhost:5173
3. Sidebar **Agent Launchpad** or Dashboard **Agent Launchpad**.
4. Green path: no red API banner → problem statement → **Start interview** → clarifying Qs → requirements.

Fresh session: http://localhost:5173/interview?fresh=1
