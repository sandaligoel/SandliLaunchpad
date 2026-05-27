# Start AFFINE (local)

See [docs/EMPLOYEE_SETUP.md](docs/EMPLOYEE_SETUP.md) for the full onboarding guide.

## Fixed ports

| Service | Port | URL |
|---------|------|-----|
| Backend API | **8003** | http://127.0.0.1:8003 |
| Mock API | **3001** | http://127.0.0.1:3001 |
| Frontend | **5173** | http://localhost:5173 |

From [config/dev-ports.json](config/dev-ports.json).

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
cd ../mock-api && npm install
```

Optional catalog index:

```bash
cd backend && source .venv/bin/activate
python scripts/create_index.py
python -m pipeline.run --source ./data/spec.json
```

## Every day

```bash
./scripts/dev-up.sh              # check ports + health

./scripts/start-backend.sh       # terminal 1
./scripts/start-mock-api.sh      # terminal 2 (Dashboard only)
cd frontend && npm run dev       # terminal 3
```

Open **http://localhost:5173/interview**

Fresh session: **http://localhost:5173/interview?fresh=1**

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Cannot reach AFFINE API | Run `./scripts/start-backend.sh` |
| Port 5173 in use | `./scripts/dev-reset.sh` |
| Dashboard errors on 3001 | Run `./scripts/start-mock-api.sh` |
| Wrong proxy port | `./scripts/sync-dev-env.sh` and restart `npm run dev` |
