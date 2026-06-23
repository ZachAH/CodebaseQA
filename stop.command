#!/bin/bash
#
# CodebaseQA stopper — double-click to shut everything down.
# Stops the dev servers and the database container. Your indexed repos persist
# in the Docker volume, so the next start.command picks up where you left off.
#
cd "$(dirname "$0")" || exit 1

echo "🦈  CodebaseQA — shutting down"

echo "→ Stopping the dev servers…"
pkill -f "manage.py runserver" 2>/dev/null && echo "  backend stopped" || echo "  backend wasn't running"
pkill -f "vite" 2>/dev/null && echo "  frontend stopped" || echo "  frontend wasn't running"

echo "→ Stopping the database container…"
docker compose stop 2>/dev/null && echo "  database stopped" || echo "  database wasn't running"

echo
echo "✅ All stopped. Data is preserved. Double-click start.command to bring it back."
echo "   (You can close the leftover server Terminal windows.)"
sleep 1
