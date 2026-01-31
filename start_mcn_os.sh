#!/bin/bash

# =============================================================================
# 🚀 MCN OS - Docker-First Startup Script
# =============================================================================
# This script launches the AI Artist Operating System using Docker containers.
# Most services run in Docker; only Sanity Studio remains native (dev server).
# =============================================================================

set -e

BASE_DIR="/home/jimmy/Documents/mcn"
cd "$BASE_DIR"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🐳 MCN OS - Docker-First Startup${NC}"
echo "========================================"

# 1. Start Core Docker Services
echo -e "${YELLOW}Step 1: Starting Core Docker Services...${NC}"
docker-compose up -d

echo -e "${GREEN}✅ Core Docker Services Started:${NC}"
echo "   - postgres, redis, mysql (Data Layer)"
echo "   - mcn-core (Middleware + BettaFish)"
echo "   - signsrv, mediacrawler (Crawler Layer)"
echo "   - cosyvoice, ollama (AI Layer)"
echo "   - n8n (Workflow Orchestration)"
echo "   - dozzle (Logs: http://localhost:8888)"

# 2. Wait for critical services
echo -e "${YELLOW}Step 2: Waiting for services to be ready...${NC}"
sleep 5

# Health check mcn-core
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ mcn-core is healthy${NC}"
else
    echo -e "${YELLOW}⏳ mcn-core is starting (check Dozzle for logs)${NC}"
fi

# 2.5. Start Redis Worker (for async tasks)
echo -e "${YELLOW}Step 2.5: Starting Redis Worker...${NC}"
cd "$BASE_DIR/middleware"
# Kill existing worker if running
if [ -f "$BASE_DIR/worker.pid" ]; then
    OLD_PID=$(cat "$BASE_DIR/worker.pid" 2>/dev/null)
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "   Stopping old worker (PID: $OLD_PID)..."
        kill "$OLD_PID" 2>/dev/null || true
        sleep 1
    fi
fi

# Start new worker using venv Python
if [ -d ".venv" ]; then
    nohup .venv/bin/python worker.py > worker.log 2>&1 &
    WORKER_PID=$!
    echo $WORKER_PID > "$BASE_DIR/worker.pid"
    echo -e "${GREEN}✅ Redis Worker started with venv (PID: $WORKER_PID)${NC}"
else
    echo -e "${YELLOW}⚠️  No .venv found, using system Python${NC}"
    nohup python3 worker.py > worker.log 2>&1 &
    WORKER_PID=$!
    echo $WORKER_PID > "$BASE_DIR/worker.pid"
    echo -e "${GREEN}✅ Redis Worker started (PID: $WORKER_PID)${NC}"
fi
echo "   - Processes queued tasks (media analysis, etc.)"
echo "   - Logs: middleware/worker.log"
cd "$BASE_DIR"

# 3. Start Sanity Studio (kept native for dev experience)
echo -e "${YELLOW}Step 3: Starting Sanity Studio (native)...${NC}"
gnome-terminal --title="Sanity Studio" --tab --working-directory="$BASE_DIR/sanity-studio" -- bash -c "
    echo '📝 Starting Sanity Content Studio...';
    npm run dev;
    exec bash" 2>/dev/null || {
    echo -e "${YELLOW}ℹ️  Start Sanity manually: cd sanity-studio && npm run dev${NC}"
}

# 4. Start Ngrok for N8N Webhooks (optional)
echo -e "${YELLOW}Step 4: Starting Ngrok tunnel...${NC}"
pkill -f "ngrok http 5678" 2>/dev/null || true
sleep 1
nohup /snap/bin/ngrok http 5678 --config ~/ngrok/ngrok.yml > /tmp/ngrok.log 2>&1 &
sleep 3

# Get ngrok public URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['tunnels'][0]['public_url'] if d.get('tunnels') else 'Not available')" 2>/dev/null || echo "Not available")

# 5. Start Vidi 7B (Native, GPU - Video Understanding)
echo -e "${YELLOW}Step 5: Starting Vidi 7B Server...${NC}"
if [ -f "$BASE_DIR/start_vidi.sh" ]; then
    gnome-terminal --title="Vidi 7B" --tab --working-directory="$BASE_DIR" -- bash -c "
        echo '🎥 Starting Vidi 7B Video Understanding...';
        ./start_vidi.sh;
        exec bash" 2>/dev/null || {
        # Fallback: run in background if no terminal
        nohup "$BASE_DIR/start_vidi.sh" > /tmp/vidi_startup.log 2>&1 &
        echo -e "${GREEN}✅ Vidi 7B starting in background${NC}"
    }
else
    echo -e "${YELLOW}ℹ️  Vidi not configured (start_vidi.sh not found)${NC}"
fi

# 6. Start ComfyUI (Native, GPU)
echo -e "${YELLOW}Step 6: Starting ComfyUI (Native)...${NC}"
gnome-terminal --title="ComfyUI" --tab --working-directory="$BASE_DIR" -- bash -c "
    echo '🎨 Starting ComfyUI on port 8188...';
    ./start_comfy.sh;
    exec bash" 2>/dev/null || {
    echo -e "${YELLOW}ℹ️  Start ComfyUI manually: ./start_comfy.sh${NC}"
}

# 6. Summary
echo ""
echo -e "${GREEN}✨ MCN OS Started Successfully!${NC}"
echo "========================================"
echo ""
echo "📦 Docker Services:"
echo "   - Middleware:    http://localhost:8000"
echo "   - Redis Worker:  Running (PID in worker.pid)"
echo "   - MediaCrawler:  http://localhost:8010"
echo "   - SignSrv:       http://localhost:8989"
echo "   - n8n:           http://localhost:5678"
echo "   - Dozzle Logs:   http://localhost:8888"
echo "   - Dashboard:     http://localhost:3000"
echo ""
echo "🔧 Native Services:"
echo "   - Sanity Studio: http://localhost:3333"
echo "   - ComfyUI:       http://localhost:8188"
echo "   - Vidi 7B:       http://localhost:8099"
echo ""
echo "🌐 Ngrok Webhook URL: ${NGROK_URL}/webhook/cookie-sync"
echo ""
echo "📋 View all logs:"
echo "   docker-compose logs -f"
echo "   OR visit http://localhost:8888 (Dozzle)"

