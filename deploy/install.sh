#!/bin/sh
# One-time setup on the Pi. Run from the repo folder:
#   sudo sh deploy/install.sh
# Installs the Python packages, then installs, enables and starts the `treadmill` service.
set -eu

[ "$(id -u)" -eq 0 ] || { echo "run with sudo: sudo sh deploy/install.sh" >&2; exit 1; }
DIR=$(cd "$(dirname "$0")/.." && pwd)
USER_NAME=${SUDO_USER:-$(stat -c %U "$DIR")}

apt-get install -y python3-gpiozero python3-lgpio python3-starlette python3-uvicorn python3-websockets

sed -e "s|@USER@|$USER_NAME|" -e "s|@DIR@|$DIR|" "$DIR/deploy/treadmill.service" \
    > /etc/systemd/system/treadmill.service
systemctl daemon-reload
systemctl enable treadmill
systemctl restart treadmill

echo "treadmill service running as $USER_NAME from $DIR"
echo "open http://$(hostname).local on a phone; logs: journalctl -u treadmill -f"
