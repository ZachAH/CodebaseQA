#!/bin/bash
#
# CodebaseQA launcher — double-click in Finder to start everything.
# Starts the database, does first-run setup if needed, then opens a Terminal
# window each for the backend and frontend, and finally opens the browser.
#
cd "$(dirname "$0")" || exit 1
ROOT="$(pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

echo "🦈  CodebaseQA — starting up"
echo "    project: $ROOT"
echo

# --- 1. Docker daemon -------------------------------------------------------
if ! docker info >/dev/null 2>&1; then
  echo "→ Docker isn't running yet — launching Docker Desktop…"
  open -a Docker 2>/dev/null || {
    echo "✗ Docker Desktop not found. Install it from https://www.docker.com/products/docker-desktop/"
    echo "  Press any key to close." ; read -r -n 1 ; exit 1
  }
  printf "  waiting for Docker"
  for _ in $(seq 1 60); do
    docker info >/dev/null 2>&1 && break
    printf "." ; sleep 2
  done
  echo
fi
if ! docker info >/dev/null 2>&1; then
  echo "✗ Docker didn't start in time. Open Docker Desktop, then run this again."
  echo "  Press any key to close." ; read -r -n 1 ; exit 1
fi

# --- 2. Database container ---------------------------------------------------
echo "→ Starting the database (Postgres + pgvector)…"
docker compose up -d || { echo "✗ docker compose failed."; read -r -n 1; exit 1; }
printf "  waiting for the database to be healthy"
for _ in $(seq 1 30); do
  status="$(docker inspect -f '{{.State.Health.Status}}' codebaseqa-db 2>/dev/null || echo none)"
  [ "$status" = "healthy" ] && break
  printf "." ; sleep 2
done
echo

# --- 3. First-run setup (only does work if something's missing) -------------
if [ ! -d "$BACKEND/.venv" ]; then
  echo "→ First run: creating the backend virtualenv + installing dependencies…"
  python3 -m venv "$BACKEND/.venv" || { echo "✗ Could not create venv (is python3 installed?)"; read -r -n 1; exit 1; }
  "$BACKEND/.venv/bin/pip" install -q --upgrade pip
  "$BACKEND/.venv/bin/pip" install -q -r "$BACKEND/requirements.txt" || { echo "✗ pip install failed."; read -r -n 1; exit 1; }
fi

if [ ! -f "$BACKEND/.env" ]; then
  cp "$BACKEND/.env.example" "$BACKEND/.env"
  echo "⚠  Created backend/.env — add your free GROQ_API_KEY (https://console.groq.com) before asking questions."
fi

echo "→ Applying database migrations…"
"$BACKEND/.venv/bin/python" "$BACKEND/manage.py" migrate >/dev/null || { echo "✗ migrate failed."; read -r -n 1; exit 1; }

if [ ! -d "$FRONTEND/node_modules" ]; then
  echo "→ First run: installing frontend dependencies…"
  ( cd "$FRONTEND" && npm install ) || { echo "✗ npm install failed (is Node installed?)"; read -r -n 1; exit 1; }
fi

# --- 4. Launch the two dev servers in their own Terminal windows ------------
echo "→ Opening backend and frontend in new Terminal windows…"
osascript >/dev/null <<OSA
tell application "Terminal"
  activate
  do script "cd '$BACKEND' && source .venv/bin/activate && echo '🦈 Backend → http://localhost:8000' && python manage.py runserver"
  do script "cd '$FRONTEND' && echo '🦈 Frontend → http://localhost:5173' && npm run dev"
end tell
OSA

# --- 5. Open the app in the browser -----------------------------------------
echo "→ Opening http://localhost:5173 …"
sleep 4
open "http://localhost:5173"

echo
echo "✅ CodebaseQA is up!  Backend :8000  •  Frontend :5173"
echo "   (Close this window anytime — the two server windows keep running.)"
echo "   To stop everything, double-click stop.command."
