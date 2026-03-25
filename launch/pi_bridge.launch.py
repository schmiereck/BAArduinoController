import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    # 1. Pfade zu den Dateien finden.
    package_name = 'BAArduinoController'
    pkg_share = get_package_share_directory(package_name)

    # Pfad zur URDF-Datei
    urdf_file = os.path.join(pkg_share, 'urdf', 'bracket_arm.urdf')

    # URDF Inhalt einlesen (für den robot_state_publisher)
    with open(urdf_file, 'r') as infp:
        robot_desc = infp.read()

    # 2. Den Robot State Publisher Node definieren.
    # Dieser Node "veröffentlicht" dein 3D-Modell im ROS-Netzwerk.
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_desc}]
    )

    # 3. Deine Hardware-Bridge (Action Server) definieren.
    # Das ist das Skript, das mit dem Arduino spricht.
    arduino_bridge_node = Node(
        package=package_name,
        executable='Ros2Bridge', # Entspricht dem Namen aus entry_points/console_scripts in setup.py
        name='robot_arm_bridge', # 'name' ist der Name, unter dem der Node im ROS-Netzwerk erscheint:
        output='screen'
    )

    # 4. Joint State Publisher (Optional, falls MoveIt noch nicht läuft)
    # Er sorgt dafür, dass alle Gelenke erst mal eine definierte Position haben
    joint_state_publisher_node = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        condition=None # Hier könnten wir später MoveIt-Kopplung prüfen
    )

    return LaunchDescription([
        robot_state_publisher_node,
        arduino_bridge_node,
        # joint_state_publisher_node # Später von MoveIt gesteuert
    ])
