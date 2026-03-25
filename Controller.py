import tkinter as tk
from tkinter import ttk
import serial
import struct
import time

#------------------------------------------------------------------------------
# --- KONFIGURATION ---
#SERIAL_PORT = '/dev/ttyACM0'  # Unter Windows z.B. 'COM3'
SERIAL_PORT = 'COM3'  # Unter Windows z.B. 'COM3'
BAUD_RATE = 115200
START_MARKER = 0xAA

#------------------------------------------------------------------------------
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    time.sleep(2) # Warten auf Arduino Reset
    print(f"Verbunden mit {SERIAL_PORT}")
except Exception as e:
    print(f"Fehler: {e}")
    ser = None

#------------------------------------------------------------------------------
# Label aktualisieren
def update_label(label_obj, val, unitStr):
    # Umwandlung von Float-String zu Int
    int_val = int(float(val))
    label_obj.config(text=str(int_val) + " " + unitStr)
    # Falls du willst, dass der Arm sofort reagiert, wenn du die Dauer änderst:
    #send_binary_packet()

#------------------------------------------------------------------------------
last_send_time = 0

def send_binary_packet(event=None):
    global last_send_time

    if not ser: return

    current_time = time.time()
    # Nur senden, wenn das Event "ButtonRelease" ist ODER 0.1s vergangen sind
    # Das verhindert das Fluten des Arduinos
    if event and event.type != '5': # '5' ist ButtonRelease in Tkinter
        if current_time - last_send_time < 0.1:
            return
    last_send_time = current_time

    # Werte aus den Schiebereglern lesen
    angles = [int(s.get()) for s in sliders]
    duration = int(duration_slider.get())

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
# --- GUI SETUP ---
#------------------------------------------------------------------------------
root = tk.Tk()
root.title("6-DOF Arm Binary Controller")
root.geometry("400x500")

sliders = []
labels =   ["Base", "Schulter", "Ellenbogen", "Hand Gelenk", "Hand Dreh", "Greifer"]
angleArr = [90,     0,          0,            160,            90,          45      ]

#------------------------------------------------------------------------------
# 1. Gelenk-Regler erstellen (OHNE command!)
ttk.Label(root, text="Gelenk-Positionen", font=('Arial', 10, 'bold')).pack(pady=10)

for pos, name in enumerate(labels):
    frame = ttk.Frame(root)
    frame.pack(pady=2, fill="x", padx=20)
    ttk.Label(frame, text=f"{name}:", width=15).pack(side="left")

    # Label, das den eigentlichen Wert anzeigt
    val_label = ttk.Label(frame, text="---", width=6, anchor="e")
    val_label.pack(side="right")

    # WICHTIG: Noch kein command übergeben, um Fehler beim Start zu vermeiden.
    # Scale erstellen:
    s = ttk.Scale(
        frame,
        from_=0,
        to=180,
        orient="horizontal",
        command=lambda v, l=val_label: update_label(l, v, "°") # Funktion Wert anzeigen
    )

    s.set(angleArr[pos])

    s.pack(side="right", expand=True, fill="x")
    sliders.append(s)

#------------------------------------------------------------------------------
# 2. Dauer-Regler erstellen:
ttk.Separator(root, orient='horizontal').pack(fill='x', pady=15)
ttk.Label(root, text="Geschwindigkeit", font=('Arial', 10, 'bold')).pack(pady=5)
dur_frame = ttk.Frame(root)
dur_frame.pack(pady=5, fill="x", padx=20)
ttk.Label(dur_frame, text="Dauer (ms):", width=15).pack(side="left")
# Label, das den eigentlichen Wert anzeigt.
dur_val_label = ttk.Label(dur_frame, text="---", width=6, anchor="e")
dur_val_label.pack(side="right")
duration_slider = ttk.Scale(
    dur_frame,
    from_=20,
    to=2000,
    orient="horizontal",
    command=lambda v, l=dur_val_label: update_label(l, v, "ms") # Funktion Wert anzeigen
)
duration_slider.set(100)
duration_slider.pack(side="right", expand=True, fill="x")

#------------------------------------------------------------------------------
# 3. Jetzt erst die Callback-Funktion an alle Slider binden
# (Jetzt sind alle Variablen definitiv definiert)
for s in sliders:
    #s.config(command=send_binary_packet)
    # Bindet das Senden an das Bewegen (mit Throttle) UND an das Loslassen (fix)
    s.bind("<B1-Motion>", send_binary_packet) # Während des Ziehens (gebremst)
    s.bind("<ButtonRelease-1>", send_binary_packet) # Beim Loslassen (immer)

#duration_slider.config(command=send_binary_packet)
duration_slider.bind("<B1-Motion>", send_binary_packet) # Während des Ziehens (gebremst)
duration_slider.bind("<ButtonRelease-1>", send_binary_packet) # Beim Loslassen (immer)

#------------------------------------------------------------------------------
# Button zum manuellen Senden (falls die Echtzeit-Übertragung hakt)
send_btn = ttk.Button(root, text="Manuell Senden", command=send_binary_packet)
send_btn.pack(pady=10)

#------------------------------------------------------------------------------
# Rückmeldungen vom Arduino anzeigen (z.B. freie Puffer-Slots)
status_label = ttk.Label(root, text="Warte auf Arduino...")
status_label.pack(pady=5)

#------------------------------------------------------------------------------
def check_serial():
    if ser and ser.in_waiting > 0:
        # Wir lesen das Byte, das der Arduino als Bestätigung schickt
        msg = ser.read()
        status_label.config(text=f"Freie Puffer-Slots: {ord(msg)}")
    root.after(50, check_serial) # Alle 50ms prüfen

#------------------------------------------------------------------------------
root.after(50, check_serial)
root.mainloop()

if ser: ser.close()

#------------------------------------------------------------------------------
