#!/bin/sh
# Start the gluetun + qBittorrent + prowlarr stack after a NAS boot.
# Run by a DSM Task Scheduler "Boot-up" task (as root). Safe to run any time:
# it only starts containers that are stopped and never recreates them.
# Why: after a reboot Container Manager skipped qBittorrent (it had exited 137).

LOG=/volume1/docker/gluetun/start-stack.log
DOCKER=/usr/local/bin/docker
exec >>"$LOG" 2>&1
echo "=== $(date '+%Y-%m-%d %H:%M:%S') start-stack ==="

# Wait up to 5 minutes for the Docker daemon.
i=0
until "$DOCKER" info >/dev/null 2>&1; do
  i=$((i + 1))
  [ "$i" -ge 60 ] && { echo "docker daemon not ready after 5 min, giving up"; exit 1; }
  sleep 5
done

cd /volume1/docker/gluetun || exit 1
# -p: the containers belong to project gluetun-qbittorrent, not the folder name.
"$DOCKER" compose -p gluetun-qbittorrent up -d --no-recreate
echo "exit=$?"
"$DOCKER" ps --filter name=gluetun --filter name=qbittorrent --filter name=prowlarr --format '{{.Names}}: {{.Status}}'
