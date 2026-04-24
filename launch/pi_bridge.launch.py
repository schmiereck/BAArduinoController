import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    package_name = 'BAArduinoController'

    # Deine Hardware-Bridge (Action Server) definieren.
    # Das ist das Skript, das mit dem Arduino spricht.
    arduino_bridge_node = Node(
        package=package_name,
        executable='Ros2Bridge', # Entspricht dem Namen aus entry_points/console_scripts in setup.py
        name='robot_arm_bridge', # 'name' ist der Name, unter dem der Node im ROS-Netzwerk erscheint:
        output='screen'
    )

    return LaunchDescription([
        arduino_bridge_node,
    ])
