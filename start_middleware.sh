#!/bin/bash
export REDIS_HOST="localhost"
export REDIS_PORT="6379"
cd /home/jimmy/Documents/mcn/middleware
source .venv/bin/activate
echo "Starting GPU Middleware (API + Worker)..."
# Start Worker in Background
python worker.py > worker.log 2>&1 &
WORKER_PID=$!
echo "Worker PID: $WORKER_PID"

# Start API in Foreground
uvicorn server:app --host 0.0.0.0 --port 8000 --reload > server.log 2>&1

# Cleanup on exit
kill $WORKER_PID
