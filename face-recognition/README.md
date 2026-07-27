# SafeGuardAI — Face Recognition

Face detection, recognition, and search module: FastAPI + InsightFace + FAISS + Postgres backend, with a React/TanStack frontend dashboard.

## Prerequisites

- Python 3.11, [uv](https://docs.astral.sh/uv/)
- Node.js 20+ (use `nvm` if your system Node is older)
- Docker
- ffmpeg (`sudo apt install -y ffmpeg`)
- NVIDIA GPU + CUDA 12.4 (CPU also works, just slower)

## Backend setup

```bash
cd backend

# install dependencies
uv sync

# GPU libraries (only needed once per machine, not per project)
uv add nvidia-cudnn-cu12   # if not already installed
```

Add this to `.venv/bin/activate` so GPU libs are found automatically every time you activate the venv:

```bash
echo 'export LD_LIBRARY_PATH='"$(pwd)"'/.venv/lib/python3.11/site-packages/nvidia/cudnn/lib:/usr/local/cuda-12.4/targets/x86_64-linux/lib:$LD_LIBRARY_PATH' >> .venv/bin/activate
source .venv/bin/activate
```

### Database (Postgres via Docker)

```bash
docker run -d \
  --name safeguardai-postgres \
  -e POSTGRES_USER=safeguard \
  -e POSTGRES_PASSWORD=safeguard_dev_pw \
  -e POSTGRES_DB=safeguardai \
  -p 5432:5432 \
  -v safeguardai_pgdata:/var/lib/postgresql/data \
  postgres:16

docker exec -i safeguardai-postgres psql -U safeguard -d safeguardai < configs/schema.sql
```

### Environment

```bash
cat > .env << 'EOF'
DATABASE_URL=postgresql://safeguard:safeguard_dev_pw@localhost:5432/safeguardai
EOF
```

### Run the API

```bash
uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000 --app-dir src
```

API docs: `http://<host>:8000/docs`

## Frontend setup

```bash
cd frontend

nvm use 20   # or: nvm install 20

npm install

cat > .env << 'EOF'
VITE_API_BASE_URL=http://<host>:8000
EOF

npm run dev
```

App: `http://<host>:8080`

## Notes

- First backend run auto-downloads the InsightFace `buffalo_l` model (~few hundred MB) to `~/.insightface/models/`.
- Liveness/anti-spoof detection is not yet implemented — planned for later.
- Face-search only matches against enrolled people (not raw footage frames).