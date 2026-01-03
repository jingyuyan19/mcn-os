#!/bin/bash
# Backup n8n workflows (Granular Strategy)

# 1. Create a temporary dir inside the container
docker exec mcn_n8n mkdir -p /home/node/.n8n/tmp_backup

# 2. Export each workflow as a separate JSON file
# --separate: Keeps files granular (one json per workflow)
# --backup: Adds timestamp (We avoid this for Git friendly usage, usually. 
# But here we want the latest state. So we just use --separate).
echo "📤 Exporting workflows from n8n internal database..."
docker exec mcn_n8n n8n export:workflow --all --separate --output=/home/node/.n8n/tmp_backup

# 3. Copy files to the host machine
# This directory should be tracked by Git
TARGET_DIR="./n8n/workflows"
mkdir -p $TARGET_DIR

echo "📥 Copying to host: $TARGET_DIR"
docker cp mcn_n8n:/home/node/.n8n/tmp_backup/. $TARGET_DIR

# 4. Clean up container
docker exec mcn_n8n rm -rf /home/node/.n8n/tmp_backup

echo "✅ Backup Complete! Don't forget to git add & commit."
echo "   Files saved in: $TARGET_DIR"
