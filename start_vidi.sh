#!/bin/bash

# =============================================================================
# Vidi 7B Server Startup Script
# =============================================================================
# Runs Vidi 7B video understanding model on port 8099
# Used for temporal grounding (finding timestamps in videos)
# =============================================================================

VIDI_DIR="/mnt/data_ssd/mcn/external/Vidi/Vidi_7B"
VIDI_PID_FILE="/mnt/data_ssd/mcn/vidi.pid"
VIDI_LOG="$VIDI_DIR/vidi_server.log"
MODEL_PATH="$VIDI_DIR/weights"
PORT=8099

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

cd "$VIDI_DIR"

# Check if already running
if [ -f "$VIDI_PID_FILE" ]; then
    OLD_PID=$(cat "$VIDI_PID_FILE" 2>/dev/null)
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo -e "${YELLOW}Vidi server already running (PID: $OLD_PID)${NC}"
        echo "To restart: kill $OLD_PID && ./start_vidi.sh"
        exit 0
    fi
fi

# Check model weights exist
if [ ! -d "$MODEL_PATH" ] && [ ! -L "$MODEL_PATH" ]; then
    echo -e "${RED}Error: Model weights not found at $MODEL_PATH${NC}"
    exit 1
fi

# Activate venv and start server
echo -e "${YELLOW}Starting Vidi 7B server on port $PORT...${NC}"
echo "Model: $MODEL_PATH"
echo "Log: $VIDI_LOG"

source "$VIDI_DIR/vidi7b_env/bin/activate"

# Start server in background with 4-bit quantization (~7GB VRAM, leaves room for other services)
nohup python vidi_server.py \
    --model "$MODEL_PATH" \
    --port $PORT \
    --load-4bit \
    > "$VIDI_LOG" 2>&1 &

VIDI_PID=$!
echo $VIDI_PID > "$VIDI_PID_FILE"

echo -e "${GREEN}Vidi server starting (PID: $VIDI_PID)${NC}"
echo "Waiting for model to load (this takes 30-60 seconds)..."

# Wait for health endpoint
for i in {1..60}; do
    if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Vidi 7B ready at http://localhost:$PORT${NC}"
        exit 0
    fi
    sleep 2
done

echo -e "${YELLOW}⏳ Vidi still loading. Check logs: tail -f $VIDI_LOG${NC}"
