# BA Arm ROS2 Bridge als systemd Service

Dieses Setup erlaubt dir, den ROS2-Bridge als systemd Service auf dem Raspberry Pi zu starten/stoppen und automatisch bei Reboot neu zu starten.

## Installation auf dem Raspberry Pi

### Schritt 1: Repository und ServiceFiles auf den Pi synchronisieren

```bash
# Via SSH vom PC aus (oder direkt auf dem Pi):
cd ~/ros2_ws/src/BAArduinoController
git pull
```

### Schritt 2: Service installieren

Auf dem **Pi** ausführen:

```bash
cd ~/ros2_ws/src/BAArduinoController
sudo bash setup-service.sh
```

Das Script installiert:
- ✓ `baarm-bridge.service` → `/etc/systemd/system/`
- ✓ `deploy.sh` → `/usr/local/bin/ba-deploy`
- ✓ ROS2-Umgebungsvariablen → `~/.ros2_env`

### Schritt 3: Service aktivieren und testen

```bash
# Service aktivieren (startet automatisch bei Reboot)
sudo systemctl enable baarm-bridge

# Service jetzt starten
sudo systemctl start baarm-bridge

# Status prüfen
sudo systemctl status baarm-bridge

# Logs live anschauen
sudo journalctl -u baarm-bridge -f
```

## Verwendung

### Service-Befehle

```bash
# Service starten
sudo systemctl start baarm-bridge

# Service stoppen
sudo systemctl stop baarm-bridge

# Service neustarten
sudo systemctl restart baarm-bridge

# Status anschauen
sudo systemctl status baarm-bridge

# Logs anschauen (letzte 50 Zeilen)
sudo journalctl -u baarm-bridge -n 50

# Logs live folgen (Ctrl+C zum Beenden)
sudo journalctl -u baarm-bridge -f
```

### Automatisches Deployment

Deploy-Script auf dem Pi ausführen:

```bash
ba-deploy
```

Das Script:
1. Stoppt den Service
2. `git pull` für Updates
3. `colcon build` mit Release-Optimierungen
4. Startet Service neu
5. Zeigt Status an

## Service-Konfiguration anpassen

Falls du Anpassungen brauchst (z.B. andere User, Workspace-Pfad):

```bash
sudo nano /etc/systemd/system/baarm-bridge.service
# Änderungen speichern (Ctrl+O, Enter, Ctrl+X)
sudo systemctl daemon-reload
sudo systemctl restart baarm-bridge
```

## Fehlerbehandlung

### Service startet nicht

```bash
# Logs detailliert anschauen
sudo journalctl -u baarm-bridge -n 100

# Syntax der Service-Datei prüfen
sudo systemctl status baarm-bridge
```

**Häufige Gründe:**
- `.bashrc` nicht lesbar (User-Berechtigungen)
- ROS-Umgebung nicht richtig sourced
- Arduino-Seriellen Port nicht gefunden (aber dann sollte der Service croppen)

### Service startet immer wieder neu

Das ist gewollt bei Fehler (`Restart=on-failure`). Prüfe die Logs mit `journalctl -f`.

Wenn du es deaktivieren möchtest:
```bash
sudo systemctl set-property baarm-bridge Restart=no
```

### Deinstallation

Falls du den Service wieder entfernen möchtest:

```bash
sudo systemctl disable baarm-bridge
sudo systemctl stop baarm-bridge
sudo rm /etc/systemd/system/baarm-bridge.service
sudo rm /usr/local/bin/ba-deploy
sudo systemctl daemon-reload
```

## Umgebungsvariablen

Der Service nutzt folgende Variablen aus `~/.ros2_env`:
- `ROS_DOMAIN_ID=1` — DDS Domain für PC-Pi Kommunikation
- `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` — Middleware
- `ROS_DISTRO=humble`

Du kannst diese in `~/.ros2_env` anpassen und dann `sudo systemctl restart baarm-bridge` ausführen.

## Tipps für Produktiveinsatz

- **Logging erweitern:** Hardcoded in `baarm-bridge.service` zu einer Datei:
  ```
  StandardOutput=append:/var/log/baarm-bridge.log
  StandardError=append:/var/log/baarm-bridge.log
  ```
  
- **CPU-Limits setzen:** Falls der Pi eine hohe CPU-Last hat:
  ```
  [Service]
  CPUQuota=80%
  ```

- **Monitorierung:** Mit `systemctl list-timers` und Custom-Scripts oder Services (z.B. Watchdog)

- **Deploy-Skript über Cron:** Tägliche Deployments möglich:
  ```bash
  sudo crontab -e
  # Beispiel: täglich 2 Uhr deployen
  0 2 * * * ba-deploy >> /var/log/ba-deploy.log 2>&1
  ```
