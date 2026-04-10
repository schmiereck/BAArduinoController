import struct
import serial
import time
import os
import sys
from dotenv import load_dotenv

#------------------------------------------------------------------------------
# --- KONFIGURATION ---
# .env suchen: erst relativ zur Quelldatei (symlink-install), dann CWD.
_pkg_dir = os.path.dirname(os.path.realpath(__file__))
_source_env = os.path.join(os.path.dirname(_pkg_dir), '.env')
if os.path.exists(_source_env):
    load_dotenv(_source_env)
else:
    # Fallback: Suche ab CWD aufwärts (Standard-Verhalten von load_dotenv)
    load_dotenv()

# Zugriff über os.getenv (mit Default-Werten als Fallback)
SERIAL_PORT = os.getenv('SERIAL_PORT', '/dev/ttyACM0')
BAUD_RATE = int(os.getenv('BAUD_RATE', 115200)) # Wichtig: Umwandlung in int!

START_MARKER = 0xAA
FLUSH_MARKER = 0xFF

#------------------------------------------------------------------------------
# Init:
# sys.stderr wird von ROS2 Launch immer angezeigt (stdout kann gepuffert sein).
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    time.sleep(2) # Warten auf Arduino Reset
    print(f"[Sender] Verbunden mit {SERIAL_PORT}", file=sys.stderr)
except Exception as e:
    print(f"[Sender] FEHLER: Serial-Verbindung fehlgeschlagen: {e} (Port: {SERIAL_PORT})", file=sys.stderr)
    ser = None

#------------------------------------------------------------------------------
def send_binary_packet(angles, duration):
    """
    Sendet ein binäres Paket an den Arduino.
    :param ser: Das aktive Serial-Objekt
    :param angles: Liste oder Array mit 6 Integern (0-180)
    :param duration: Integer (Dauer in ms)
    """
    if not ser: return

    # SICHERHEITS-CHECK: Nur senden, wenn alle 6 Winkel da sind
    if len(angles) != 6:
        return

    # 1. Payload packen: 6x unsigned char (B), 1x unsigned short (H)
    # '<' bedeutet Little Endian (wichtig für Arduino)
    try:
        payload = struct.pack('<6BH', *angles, duration)

        # 2. Checksumme berechnen (XOR über alle 8 Bytes der Payload)
        crc = 0
        for byte in payload:
            crc ^= byte

        # 3. Komplettes Paket senden: Start-Marker + Payload + CRC
        packet = struct.pack('B', START_MARKER) + payload + struct.pack('B', crc)
        ser.write(packet)
    except struct.error as e:
        print(f"Pack-Fehler: {e}")

    # Feedback in der Konsole
    # print(f"Gesendet: {angles} | Dauer: {duration} ms | CRC: {hex(crc)}")

#------------------------------------------------------------------------------
def read_in_waiting():
    """
    Liest verfügbare Bestätigungs-Bytes vom Arduino.
    Gibt den Zahlenwert (int) des letzten Bytes zurück oder None.
    """
    if ser and ser.in_waiting > 0:
        try:
            # Wir lesen alle verfügbaren Bytes, uns interessiert aber nur das aktuellste
            # Das leert auch den Puffer, falls der PC mal kurz hing.
            data = ser.read(ser.in_waiting)
            # In Python 3 liefert ser.read() ein bytes-Objekt.
            # Der Zugriff auf den Index [ -1 ] gibt uns direkt den Integer-Wert.
            return data[-1]
        except Exception as e:
            print(f"Read-Fehler: {e}")
            return None
    return None

#------------------------------------------------------------------------------
def send_flush():
    """
    Sendet den FLUSH_MARKER, um den Puffer im Arduino zu leeren
    und die aktuelle Bewegung sofort zu stoppen.
    """
    if ser:
        try:
            ser.write(struct.pack('B', FLUSH_MARKER))
            # Optional: Kurze Pause, damit der Arduino Zeit hat zu reagieren
            # time.sleep(0.01)
        except Exception as e:
            print(f"Fehler beim Senden des Flush-Markers: {e}")

#------------------------------------------------------------------------------
def close_sender():
    if ser: ser.close()

#------------------------------------------------------------------------------