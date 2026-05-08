#!/bin/bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="$REPO_DIR/.venv"
SYSTEMD_DIR=/etc/systemd/system
UNITS=(
    stay-watch-scan.service
    stay-watch-scan.timer
    stay-watch-post.service
    stay-watch-post.timer
)

if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$REPO_DIR/requirements.txt"

for unit in "${UNITS[@]}"; do
    sed "s|__REPO_DIR__|$REPO_DIR|g" "$REPO_DIR/systemd/$unit" \
        | sudo tee "$SYSTEMD_DIR/$unit" > /dev/null
    sudo chmod 644 "$SYSTEMD_DIR/$unit"
done

sudo systemctl daemon-reload
sudo systemctl enable --now stay-watch-scan.timer stay-watch-post.timer

echo
echo "Installed. Useful commands:"
echo "  systemctl list-timers 'stay-watch-*'"
echo "  journalctl -u stay-watch-scan.service -u stay-watch-post.service -f"
