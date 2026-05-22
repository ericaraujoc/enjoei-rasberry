#!/bin/bash
set -e

# ── Raspberry Pi setup script for enjoei-bot ─────────────────────────────────
# Requires: Raspberry Pi OS 64-bit (aarch64) — Playwright needs 64-bit for Chromium

echo "=== Checking architecture ==="
ARCH=$(uname -m)
if [[ "$ARCH" != "aarch64" && "$ARCH" != "x86_64" ]]; then
    echo "ERROR: Unsupported architecture '$ARCH'."
    echo "Playwright requires 64-bit OS. Please install Raspberry Pi OS 64-bit."
    exit 1
fi
echo "Architecture OK: $ARCH"

echo ""
echo "=== Installing system dependencies ==="
sudo apt-get update -q
sudo apt-get install -y python3 python3-pip python3-venv

echo ""
echo "=== Creating virtual environment ==="
python3 -m venv venv
source venv/bin/activate

echo ""
echo "=== Installing Python packages ==="
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo ""
echo "=== Installing Playwright Chromium ==="
playwright install chromium
playwright install-deps chromium

echo ""
echo "=== Setting up .env ==="
if [ ! -f .env ]; then
    cp .env.example .env
    echo ">>> Please edit .env with your TELEGRAM_TOKEN and TELEGRAM_USER_ID, then re-run:"
    echo "    sudo bash install.sh --service"
    exit 0
fi

echo ""
echo "=== Installing systemd service ==="
sudo cp enjoei.service /etc/systemd/system/enjoei.service
sudo systemctl daemon-reload
sudo systemctl enable enjoei
sudo systemctl restart enjoei

echo ""
echo "=== Done! ==="
echo "Service status:"
sudo systemctl status enjoei --no-pager
echo ""
echo "Useful commands:"
echo "  sudo systemctl status enjoei   — check status"
echo "  sudo journalctl -u enjoei -f   — live logs"
echo "  sudo systemctl restart enjoei  — restart"
