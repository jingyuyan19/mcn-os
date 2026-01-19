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
nohup ngrok http 5678 --log=stdout > /tmp/ngrok.log 2>&1 &
sleep 3

# Get ngrok public URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['tunnels'][0]['public_url'] if d.get('tunnels') else 'Not available')" 2>/dev/null || echo "Not available")

# 5. Summary
echo ""
echo -e "${GREEN}✨ MCN OS Started Successfully!${NC}"
echo "========================================"
echo ""
echo "📦 Docker Services:"
echo "   - Middleware:    http://localhost:8000"
echo "   - MediaCrawler:  http://localhost:8001"
echo "   - SignSrv:       http://localhost:8989"
echo "   - n8n:           http://localhost:5678"
echo "   - Dozzle Logs:   http://localhost:8888"
echo ""
echo "🔧 Native Services:"
echo "   - Sanity Studio: http://localhost:3333"
echo ""
echo "🌐 Ngrok Webhook URL: ${NGROK_URL}/webhook/cookie-sync"
echo ""
echo "🎨 To start ComfyUI (GPU-intensive):"
echo "   docker-compose --profile art up -d comfyui"
echo ""
echo "📋 View all logs:"
echo "   docker-compose logs -f"
echo "   OR visit http://localhost:8888 (Dozzle)"
