# docker/mcn-core.Dockerfile
# The "Citadel" - Middleware + BettaFish + Vidi in one container
# Based on Gemini Deep Think Pragmatic Monolith recommendation

FROM python:3.11-slim-bookworm

# 1. System Dependencies
# fonts-liberation: Required for WeasyPrint to render text in PDFs correctly
# libgl1: Required for OpenCV (Vidi)
# procps: Adds 'pkill' for process management
RUN apt-get update && apt-get install -y \
    build-essential curl git procps \
    libpango-1.0-0 libpangoft2-1.0-0 libcairo2 \
    libgdk-pixbuf2.0-0 ffmpeg libsm6 libxext6 \
    fonts-liberation libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Python Dependencies
COPY docker/requirements-core.txt /tmp/requirements.txt
# --no-cache-dir reduces image size
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# 3. Playwright (Browsers)
# Only install Chromium dependencies to keep image lighter
RUN pip install playwright && playwright install chromium --with-deps

# 4. Environment Setup
ENV PYTHONPATH="/app/external/BettaFish:/app/middleware:/app/external/Vidi:${PYTHONPATH}"
ENV BETTAFISH_PATH="/app/external/BettaFish"
ENV PYTHONUNBUFFERED=1

# 5. Application Runtime
WORKDIR /app/middleware

# CRITICAL: Watch both directories for changes (Hot-reload fix from Deep Think)
CMD ["uvicorn", "server:app", \
    "--host", "0.0.0.0", \
    "--port", "8000", \
    "--reload", \
    "--reload-dir", "/app/middleware", \
    "--reload-dir", "/app/external/BettaFish"]
