import tkinter as tk
from tkinter import ttk
import time
import Sender
import json

#------------------------------------------------------------------------------
# --- KONFIGURATION ---
# Konfiguration laden
def load_config(file_path='config.json'):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Config-Datei nicht gefunden! Nutze Standardwerte.")
        return None

config = load_config()

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

def send_binary_packet_slider(event=None):
    global last_send_time

    current_time = time.time()
    # Nur senden, wenn das Event "ButtonRelease" ist ODER 0.1s vergangen sind.
    # Das verhindert das Fluten des Arduinos
    if event and event.type != '5': # '5' ist ButtonRelease in Tkinter
        if current_time - last_send_time < 0.1:
            return
    last_send_time = current_time

    """Sammelt UI-Werte und ruft den Sender auf."""
    # Werte aus den Schiebereglern lesen und Winkel-Array erstellen
    current_angles = [int(s.get()) for s in sliderArr]
    # Einzellwert für Duration
    current_duration = int(duration_slider.get())

    Sender.send_binary_packet(current_angles, current_duration)

#------------------------------------------------------------------------------
# --- GUI SETUP ---
#------------------------------------------------------------------------------
root = tk.Tk()
root.title("6-DOF Arm Binary Controller")
root.geometry("400x500")

sliderArr = []
# Werte extrahieren (mit Fallback-Sicherheit)
if config:
    labelArr = config['servos']['labels']
    angleArr = config['servos']['offsets'] # Deine Startwinkel
    default_duration = config['servos']['default_duration']
else:
    # Fallback, falls die Datei fehlt
    labelArr = ["Base", "Schulter", "Ellenbogen", "Hand Gelenk", "Hand Dreh", "Greifer"]
    angleArr = [90,     0,          0,            160,            90,          45      ]
    default_duration = 100

#------------------------------------------------------------------------------
# 1. Gelenk-Regler erstellen (OHNE command!)
ttk.Label(root, text="Gelenk-Positionen", font=('Arial', 10, 'bold')).pack(pady=10)

for pos, name in enumerate(labelArr):
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
    sliderArr.append(s)

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
duration_slider.set(default_duration)
duration_slider.pack(side="right", expand=True, fill="x")

#------------------------------------------------------------------------------
# 3. Jetzt erst die Callback-Funktion an alle Slider binden
# (Jetzt sind alle Variablen definitiv definiert)
for s in sliderArr:
    #s.config(command=send_binary_packet_slider)
    # Bindet das Senden an das Bewegen (mit Throttle) UND an das Loslassen (fix)
    s.bind("<B1-Motion>", send_binary_packet_slider) # Während des Ziehens (gebremst)
    s.bind("<ButtonRelease-1>", send_binary_packet_slider) # Beim Loslassen (immer)

#duration_slider.config(command=send_binary_packet_slider)
duration_slider.bind("<B1-Motion>", send_binary_packet_slider) # Während des Ziehens (gebremst)
duration_slider.bind("<ButtonRelease-1>", send_binary_packet_slider) # Beim Loslassen (immer)

#------------------------------------------------------------------------------
# Button zum manuellen Senden (falls die Echtzeit-Übertragung hakt)
send_btn = ttk.Button(root, text="Manuell Senden", command=send_binary_packet_slider)
send_btn.pack(pady=10)

#------------------------------------------------------------------------------
# Rückmeldungen vom Arduino anzeigen (z.B. freie Puffer-Slots)
status_label = ttk.Label(root, text="Warte auf Arduino...")
status_label.pack(pady=5)

#------------------------------------------------------------------------------
def check_serial():
    msg = Sender.read_in_waiting()
    if msg:
        status_label.config(text=f"Freie Puffer-Slots: {ord(msg)}")
    #if ser and ser.in_waiting > 0:
    #    # Wir lesen das Byte, das der Arduino als Bestätigung schickt
    #    msg = ser.read()
    #    status_label.config(text=f"Freie Puffer-Slots: {ord(msg)}")
    root.after(50, check_serial) # Alle 50ms prüfen

#------------------------------------------------------------------------------
root.after(50, check_serial)
root.mainloop()

Sender.close_sender()

#------------------------------------------------------------------------------
