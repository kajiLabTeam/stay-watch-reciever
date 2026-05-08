#!/bin/bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SYSTEMD_DIR=/etc/systemd/system
UNITS=(
    stay-watch-scan.service
    stay-watch-scan.timer
    stay-watch-post.service
    stay-watch-post.timer
)

sudo pip3 install -r "$REPO_DIR/requirements.txt"

for unit in "${UNITS[@]}"; do
    sudo install -m 644 -o root -g root \
        "$REPO_DIR/systemd/$unit" "$SYSTEMD_DIR/$unit"
done

sudo systemctl daemon-reload
sudo systemctl enable --now stay-watch-scan.timer stay-watch-post.timer

echo
echo "Installed. Useful commands:"
echo "  systemctl list-timers 'stay-watch-*'"
echo "  journalctl -u stay-watch-scan.service -u stay-watch-post.service -f"
