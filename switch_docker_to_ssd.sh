#!/bin/bash
set -e

# Check for root
if [ "$EUID" -ne 0 ]; then 
  echo "Please run as root (use sudo)"
  exit 1
fi

NEW_DATA_ROOT="/mnt/data_ssd/docker"
DAEMON_CONFIG="/etc/docker/daemon.json"

echo "Stopping Docker..."
systemctl stop docker

echo "Creating new data directory: $NEW_DATA_ROOT"
mkdir -p "$NEW_DATA_ROOT"

echo "Migrating data (using rsync)..."
# Using rsync -aP to preserve permissions/ownership/times
if [ -d "/var/lib/docker" ]; then
    rsync -aP /var/lib/docker/ "$NEW_DATA_ROOT/"
fi

echo "Configuring Docker daemon..."
# Check if daemon.json exists
if [ -f "$DAEMON_CONFIG" ]; then
    # Backup existing
    cp "$DAEMON_CONFIG" "${DAEMON_CONFIG}.bak"
    # Simple check if json is valid or if we can append. 
    # For now, we'll write a new one but print a warning.
    echo "WARNING: Overwriting existing daemon.json from backup."
fi

# Write new config
cat > "$DAEMON_CONFIG" <<EOF
{
    "data-root": "$NEW_DATA_ROOT",
    "runtimes": {
        "nvidia": {
            "path": "nvidia-container-runtime",
            "runtimeArgs": []
        }
    }
}
EOF

echo "Restarting Docker..."
systemctl start docker

echo "Verifying..."
docker info | grep "Docker Root Dir"
echo "Success! Docker is now using SSD."
