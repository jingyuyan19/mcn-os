#!/bin/bash
set -e

# Check for root
if [ "$EUID" -ne 0 ]; then 
  echo "Please run as root (use sudo)"
  exit 1
fi

SOURCE_DIR="/home/jimmy/Documents/mcn"
TARGET_DIR="/mnt/data_ssd/mcn"

echo "Stopping Docker containers..."
if [ -d "$SOURCE_DIR" ]; then
    cd "$SOURCE_DIR" || exit
    docker-compose down || echo "Docker-compose down failed, continuing anyway..."
fi

echo "Moving project from $SOURCE_DIR to $TARGET_DIR..."
# Ensure target parent exists
mkdir -p /mnt/data_ssd

# Move the directory using rsync to preserve ALL attributes (including root ownership for DBs)
# -a: archive mode (recursive, preserves permissions, owners, groups, times)
# -P: show progress
rsync -aP "$SOURCE_DIR/" "$TARGET_DIR/"

echo "Verifying copy..."
if [ -f "$TARGET_DIR/docker-compose.yml" ]; then
    echo "Copy successful."
    
    # Remove original (safe because we verified copy)
    echo "Removing original directory..."
    rm -rf "$SOURCE_DIR"
    
    # Create symlink
    echo "Creating symlink..."
    ln -s "$TARGET_DIR" "$SOURCE_DIR"
    
    # Fix ownership of the Symlink itself (and parent dir if needed, but not recursive data)
    # The data inside mcn/postgres etc MUST remain owned by their container users (uid 999 etc)
    # But the symlink should be owned by jimmy for convenience
    chown -h jimmy:jimmy "$SOURCE_DIR"
    
    echo "Success! Project moved to SSD."
else
    echo "Copy failed! Aborting removal."
    exit 1
fi
