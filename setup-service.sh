#!/bin/bash
# Setup-Script für ba-arm-bridge Service auf dem Raspberry Pi
# Führe dieses Script nur einmal aus!

set -e

SERVICE_NAME="baarm-bridge"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "BA Arm ROS2 Bridge - Service Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Prüfe ob Script als root läuft
if [[ $EUID -ne 0 ]]; then
   echo "✗ Dieses Script muss mit sudo ausgeführt werden!"
   exit 1
fi

# Bestimme den echten User und Workspace-Pfad (funktioniert auch mit sudo)
if [ -n "$SUDO_USER" ]; then
    REAL_USER="$SUDO_USER"
    REAL_HOME="/home/$SUDO_USER"
else
    REAL_USER="pi"
    REAL_HOME="/home/pi"
fi
WORKSPACE_DIR="$REAL_HOME/ros2_ws"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "User: $REAL_USER"
echo "Workspace: $WORKSPACE_DIR"
echo "Script-Pfad: $SCRIPT_DIR"
echo ""

# 1. Kopiere Service-File
echo "[1/3] Installiere systemd Service..."
if [ -f "$SCRIPT_DIR/baarm-bridge.service" ]; then
    # Kopiere und passe User + Pfade an
    TEMP_SERVICE=$(mktemp)
    sed "s|User=pi|User=$REAL_USER|g; s|/home/pi|$REAL_HOME|g" "$SCRIPT_DIR/baarm-bridge.service" > "$TEMP_SERVICE"
    mv "$TEMP_SERVICE" /etc/systemd/system/baarm-bridge.service
    chmod 644 /etc/systemd/system/baarm-bridge.service
    systemctl daemon-reload
    echo "✓ Service-Datei installiert (User: $REAL_USER, Home: $REAL_HOME)"
else
    echo "✗ baarm-bridge.service nicht gefunden in $SCRIPT_DIR"
    exit 1
fi

# 2. Kopiere Deploy-Script
echo "[2/3] Installiere Deploy-Script..."
if [ -f "$SCRIPT_DIR/deploy.sh" ]; then
    cp "$SCRIPT_DIR/deploy.sh" /usr/local/bin/ba-deploy
    chmod +x /usr/local/bin/ba-deploy
    echo "✓ Deploy-Script installiert (Befehl: ba-deploy)"
else
    echo "✗ deploy.sh nicht gefunden"
    exit 1
fi

# 3. Erstelle ROS2-Umgebungs-Datei (optional)
echo "[3/3] Konfiguriere Umgebungsvariablen..."
cat > $REAL_HOME/.ros2_env << EOF
ROS_DISTRO=humble
ROS_DOMAIN_ID=1
RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
CYCLONEDDS_URI=file://$REAL_HOME/cyclonedds.xml
EOF
chown $REAL_USER:$REAL_USER $REAL_HOME/.ros2_env
chmod 600 $REAL_HOME/.ros2_env
chown $REAL_USER:$REAL_USER $REAL_HOME/.ros2_env
chmod 600 $REAL_HOME/.ros2_env
echo "✓ ROS2-Umgebungsvariablen konfiguriert"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✓ Setup abgeschlossen!"
echo ""
echo "Nächste Schritte:"
echo "  1. Service aktivieren:"
echo "     sudo systemctl enable $SERVICE_NAME"
echo ""
echo "  2. Service testen:"
echo "     sudo systemctl start $SERVICE_NAME"
echo "     sudo systemctl status $SERVICE_NAME"
echo ""
echo "  3. Logs anschauen:"
echo "     sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "Tipps:"
echo "  • Deploy-Script: ba-deploy"
echo "  • Service nachbearbeiten: sudo nano /etc/systemd/system/$SERVICE_NAME.service"
echo "  • Service deaktivieren: sudo systemctl disable $SERVICE_NAME"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
