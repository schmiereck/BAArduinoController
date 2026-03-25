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

    # Falls "Manuell Senden" aktiv ist und ein Slider-Event (Ziehen/Klicken) reinkommt: Ignorieren
    if event and manual_mode_var.get():
        return

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
def go_home():
    """Fährt die Servos in der gewünschten Reihenfolge (1, 2, 3, 4, 0, 5) in Parkposition."""
    # Reihenfolge laut Vorgabe
    sequence = [1, 2, 3, 4, 0, 5]

    # Geschwindigkeit für Homing (etwas langsamer für Sicherheit)
    home_duration = 1000
    duration_slider.set(home_duration)

    for idx in sequence:
        # Zielwinkel aus der Config (Offsets) holen
        home_angle = angleArr[idx]
        # Slider in der GUI aktualisieren (das triggert update_label)
        sliderArr[idx].set(home_angle)

        # Paket senden (da go_home kein Event ist, ignoriert es die Checkbox-Sperre)
        send_binary_packet_slider()

        # Kurze Pause, damit der Arduino den Punkt verarbeitet, bevor der nächste kommt
        # So entsteht die nacheinander ablaufende Bewegung
        time.sleep(0.3)

#------------------------------------------------------------------------------
# --- GUI SETUP ---
#------------------------------------------------------------------------------
root = tk.Tk()
root.title("6-DOF Arm Binary Controller")
root.geometry("400x650") # Höhe leicht angepasst für neue Buttons

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
# 4. Steuerung & Modus
ttk.Separator(root, orient='horizontal').pack(fill='x', pady=15)

manual_mode_var = tk.BooleanVar(value=False)
chk_manual = ttk.Checkbutton(root, text="Manuelle Übertragung (Echtzeit aus)", variable=manual_mode_var)
chk_manual.pack(pady=5)

# Button zum manuellen Senden (falls die Echtzeit-Übertragung hakt)
send_btn = ttk.Button(root, text="Aktuelle Position senden", command=send_binary_packet_slider)
send_btn.pack(pady=5)

# Home Button
home_btn = ttk.Button(root, text="Parkposition (Homing)", command=go_home)
home_btn.pack(pady=5)

#------------------------------------------------------------------------------
# Rückmeldungen vom Arduino anzeigen (z.B. freie Puffer-Slots)
status_label = ttk.Label(root, text="Warte auf Arduino...")
status_label.pack(pady=10)

#------------------------------------------------------------------------------
def check_serial():
    # Wir lesen das Byte, das der Arduino als Bestätigung schickt
    slots = Sender.read_in_waiting()
    if slots is not None:
        status_label.config(text=f"Freie Puffer-Slots: {slots}")

    root.after(50, check_serial) # Alle 50ms prüfen

#------------------------------------------------------------------------------
root.after(50, check_serial)
root.mainloop()

Sender.close_sender()

#------------------------------------------------------------------------------