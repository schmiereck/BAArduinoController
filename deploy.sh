#!/bin/bash
# Deploy-Script für BA Arm ROS2 Bridge
# Pullt Updates, baut neu und startet Service neu

set -e  # Exit on error

WORKSPACE_DIR="$HOME/ros2_ws"
PACKAGE_NAME="BAArduinoController"
SERVICE_NAME="baarm-bridge"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "BA Arm ROS2 Bridge - Deploy Script"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Stoppe Service
echo ""
echo "[1/4] Stoppe Service..."
sudo systemctl stop $SERVICE_NAME || true
sleep 2

# 2. Git Pull
echo "[2/4] Pullen von Git-Updates..."
cd "$WORKSPACE_DIR/src/$PACKAGE_NAME"
git pull origin main || git pull origin master || echo "⚠ Git pull fehlgeschlagen (offline?)"

# 3. Build
echo "[3/4] Baue Projekt mit colcon..."
cd "$WORKSPACE_DIR"
source ~/.bashrc
micromamba activate ros_env 2>/dev/null || source /opt/ros/humble/setup.bash
colcon build --packages-select $PACKAGE_NAME --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release

# 4. Starte Service neu
echo "[4/4] Starte Service neu..."
sudo systemctl restart $SERVICE_NAME

# Status
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Service Status ━━━━━━━"
sudo systemctl status $SERVICE_NAME --no-pager | tail -10
echo ""
echo "✓ Deploy abgeschlossen!"
echo ""
echo "Tipps:"
echo "  • Status prüfen:     sudo systemctl status $SERVICE_NAME"
echo "  • Logs anschauen:    sudo journalctl -u $SERVICE_NAME -f"
echo "  • Service stoppen:   sudo systemctl stop $SERVICE_NAME"
echo "  • Service starten:   sudo systemctl start $SERVICE_NAME"
