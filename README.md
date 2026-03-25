# Bracket Arm
Ein einfacher 4-DOF-Roboterarm, der mit einem Raspberry Pi und ROS2 gesteuert wird. 

https://gemini.google.com/app/92269f0e200198ac?hl=de

```aiignore
───→
╭───────────────────────────────────────────────────────────────────────┐
│                                                                       │
│  BAArduinoController-Movelt2/RViz (ROS2-PC)                           │
│     │                                                                 │
│     ↓ ROS-Protokoll (DDS) + Action (WLAN-Network)                     │
│  BAArduinoController-ROS2Bridge/robot_state_publisher (Raspberry Pi)  │
│     │                                                                 │
│     ↓ Serial (USB)                                                    │
│  sketch_Client-PCA9685 (Arduino)                                      │
│     │                                                                 │
│     ↓ I2C                                                             │
│  PCA9685                                                              │
└───────────────────────────────────────────────────────────────────────┘ 
```

## GUIController
### Wie du es baust und startest
Raspberry Pi (Linux):  
venv:  
```sudo apt-get install python3-venv -y```  
tkinter & ttk:  
```sudo apt-get install python3-tk```  
```source venv/bin/activate```  

```pip install -r requirements.txt```  
```sudo usermod -a -G dialout $USER```  
```python GUIController.py```  

## ROS2
### Wie du es baust und startest
1. **Abhängigkeiten installieren:**  
   Gehe in deinen Workspace-Root (dev_ws) und lass rosdep die Arbeit machen:
   ```rosdep install -i --from-path src --rosdistro humble -y```
2. **Bauen:**  
   ```colcon build --packages-select my_robot_arm```
3. **Sourcen:**  
   ```source install/setup.bash```
3. **Ausführen:**  
   ```ros2 launch BAArduinoController pi_bridge.launch.py```

**Pro-Tipp**: Wenn du an deinem Python-Code arbeitest, nutze 
```colcon build --symlink-install```.  
Dann musst du nicht nach jeder kleinen Änderung im Python-Skript neu bauen!

### ROS2-PC
3. **Ausführen:**  
```ros2 launch moveit_setup_assistant setup_assistant.launch.py```.  


### Movelt
Base bis Schulter: 82 mm
Wie hoch ist das erste Segment?

Schulter bis Ellenbogen: 98 mm
Wie lang ist der Oberarm?

Ellenbogen bis Handgelenk: 66 mm
Wie lang ist der Unterarm?

Handgelenk bis Greifer-Gelenk: 103 mm
Greifer-Gelenk bis Greiferspitze: 70 mm

Handgelenk bis Greiferspitze: 103 mm + 70 mm = 173 mm
Wie weit ragt die Hand heraus?
