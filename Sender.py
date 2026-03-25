import struct
import serial
import time
import os
from dotenv import load_dotenv

#------------------------------------------------------------------------------
# --- KONFIGURATION ---
# Lädt die Variablen aus der .env Datei in das Betriebssystem-Environment
load_dotenv()

# Zugriff über os.getenv (mit Default-Werten als Fallback)
SERIAL_PORT = os.getenv('SERIAL_PORT', '/dev/ttyACM0')
BAUD_RATE = int(os.getenv('BAUD_RATE', 115200)) # Wichtig: Umwandlung in int!

START_MARKER = 0xAA

#------------------------------------------------------------------------------
# Init:
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    time.sleep(2) # Warten auf Arduino Reset
    print(f"Verbunden mit {SERIAL_PORT}")
except Exception as e:
    print(f"Fehler: {e}")
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
    if ser and ser.in_waiting > 0:
        # Wir lesen das Byte, das der Arduino als Bestätigung schickt
        msg = ser.read()
    else:
        msg = None
    return msg

#------------------------------------------------------------------------------
def close_sender():
    if ser: ser.close()

#------------------------------------------------------------------------------
