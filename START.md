# Start AFFINE (local)

See [docs/EMPLOYEE_SETUP.md](docs/EMPLOYEE_SETUP.md) for the full onboarding guide.

## Ports (auto-aligned)

Default ports: **8003** (API) / **5173** (UI). No mock server.

If a port is busy, `./scripts/allocate-ports.sh` picks the next free port and writes [config/runtime-ports.json](config/runtime-ports.json). Backend and frontend both read that file so proxies never drift.

After starting the backend, run `./scripts/sync-dev-env.sh` (or `npm run dev`, which runs it via `predev`) before using the UI.

## One-time setup

```bash
./scripts/sync-dev-env.sh

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — Azure OpenAI, Search, Blob (see docs/WHAT_TO_SHARE.md)

cd ../frontend && npm install
```

Optional catalog index:

```bash
cd backend && source .venv/bin/activate
python scripts/create_index.py
python -m pipeline.run --source ./data/spec.json
```

## Every day

```bash
./scripts/doctor.sh              # check ports + health

./scripts/start-backend.sh       # terminal 1
cd frontend && npm run dev       # terminal 2
```

Open **http://localhost:5173/interview**

Fresh session: **http://localhost:5173/interview?fresh=1**

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Cannot reach AFFINE API | Run `./scripts/start-backend.sh` |
| Port 5173 in use | `./scripts/dev-reset.sh` |
| Dashboard empty | Start backend; metrics come from saved sessions/workflows |
| Wrong proxy port | `./scripts/sync-dev-env.sh` and restart `npm run dev` |
