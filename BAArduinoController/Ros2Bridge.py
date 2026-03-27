import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, CancelResponse
from control_msgs.action import FollowJointTrajectory
from sensor_msgs.msg import JointState
from . import Sender
import time

# Ersetze <ros-distro> durch deine Version, z.B. humble
#sudo apt update
#sudo apt install ros-<ros-distro>-rclpy
#sudo apt install ros-<ros-distro>-control-msgs
#
# ROS 2-Umgebung:
#source /opt/ros/.../setup.bash

class Ros2Bridge(Node):
    def __init__(self):
        super().__init__('ros2_bridge')

        # Aktuelle Gelenkwinkel (in Radiant)
        #self._current_positions = [0.0, 1.5708, 0.0, 3.14, 1.5708, 0.0]
        self._current_positions = [0.0, 0.0, 0.0, 3.14, 1.5708, 0.0]

        # JointState Publisher
        self._joint_state_publisher = self.create_publisher(
            JointState, '/joint_states', 10)

        # Timer: publiziert joint_states 10x pro Sekunde
        self._timer = self.create_timer(0.1, self.publish_joint_states)

        # Action Server
        self._action_server = ActionServer(
            self,
            FollowJointTrajectory,
            '/arm_controller/follow_joint_trajectory',
            execute_callback=self.execute_callback,
            cancel_callback=self.cancel_callback
        )

        self.get_logger().info('Robot Arm Bridge Node gestartet und bereit...')

    def publish_joint_states(self):
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = ['joint_0', 'joint_1', 'joint_2', 'joint_3', 'joint_4', 'joint_5']
        msg.position = self._current_positions
        msg.velocity = [0.0] * 6
        msg.effort = [0.0] * 6
        self._joint_state_publisher.publish(msg)

    def cancel_callback(self, goal_handle):
        """Wird aufgerufen, wenn MoveIt die Bewegung abbricht."""
        self.get_logger().warn('Bewegung abgebrochen! Sende FLUSH an Arduino...')
        Sender.send_flush()
        return CancelResponse.ACCEPT

    async def execute_callback(self, goal_handle):
        """Verarbeitet die Trajektorie von MoveIt."""
        trajectory = goal_handle.request.trajectory
        joint_names = trajectory.joint_names
        points = trajectory.points

        self.get_logger().info(f'Empfange Trajektorie mit {len(points)} Punkten.')

        # 1. Mapping erstellen: Welcher Name liegt an welchem Index im ROS-Array?
        # Beispiel: {'joint_0': 0, 'joint_1': 1, ...}
        name_to_ros_idx = {name: i for i, name in enumerate(joint_names)}

        # Die erwarteten Namen (müssen exakt mit der URDF übereinstimmen).
        expected_joints = ['joint_0', 'joint_1', 'joint_2', 'joint_3', 'joint_4', 'joint_5']

        for i, point in enumerate(points):
            # Prüfen, ob die Action abgebrochen wurde.
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                return FollowJointTrajectory.Result()

            # 2. Winkel in der richtigen Reihenfolge (0-5) für den Arduino sammeln.
            angles_deg = []
            for servo_idx, joint_name in enumerate(expected_joints):
                if joint_name in name_to_ros_idx:
                    ros_idx = name_to_ros_idx[joint_name]
                    rad = point.positions[ros_idx]

                    # Umrechnung mit Offsets
                    deg = self.map_ros_to_servo(servo_idx, rad)
                    angles_deg.append(deg)
                else:
                    # Fallback falls ein Gelenk fehlt (sollte nicht passieren).
                    self.get_logger().error(f'Gelenk {joint_name} nicht in Trajektorie!')
                    angles_deg.append(90)

                    # Zeitdauer zum nächsten Punkt berechnen
            if i == 0:
                duration_ms = 200 # Erster Punkt Puffer
            else:
                prev_point = points[i-1]
                diff = (point.time_from_start.sec - prev_point.time_from_start.sec) + \
                    (point.time_from_start.nanosec - prev_point.time_from_start.nanosec) * 1e-9
                duration_ms = int(diff * 1000)

                # Sicherheits-Minimum für den Arduino
                duration_ms = max(20, duration_ms)

            # An Arduino senden
            Sender.send_binary_packet(angles_deg, duration_ms)

            ros_idx_list = [name_to_ros_idx.get(name) for name in expected_joints]
            self._current_positions = [
                point.positions[idx] if idx is not None else 0.0
                for idx in ros_idx_list
            ]

            # Kurze Pause, um den Puffer am Arduino nicht zu überrennen.
            while True:
                free_slots = Sender.read_in_waiting()
                # Wir warten nur, wenn wir wirklich wissen, dass der Puffer voll ist (slots <= 1)
                if free_slots is None or free_slots > 1:
                    break
                time.sleep(0.01)

        goal_handle.succeed()
        result = FollowJointTrajectory.Result()
        self.get_logger().info('Trajektorie erfolgreich ausgeführt.')
        return result

    def map_ros_to_servo(self, joint_index, angle_rad):
        """Wandelt ROS-Radianten (relativ) in Arduino-Grade (absolut) um."""
        # Offsets aus deiner Konfiguration: [Base, Schulter, Ellenbogen, Hand G, Hand D, Greifer]
        offsets = [90, 0, 0, 180, 90, 45]

        # Radianten in Grad umrechnen (1 rad ≈ 57.2958°)
        angle_deg = angle_rad * 57.2958

        # Berechnung basierend auf der Ruhestellung.
        # Joint 3 (Hand Gelenk) hat Offset 180 und klappt nach 'unten' (negative Radianten).
        # Wenn MoveIt -1.57 rad (90°) sendet -> 180 + (-90) = 90° am Servo. Passt!
        servo_angle = offsets[joint_index] + angle_deg

        # Sicherstellen, dass wir innerhalb der 0-180 Grad Hardware-Limits bleiben
        return int(max(0, min(180, servo_angle)))

def main(args=None):
    rclpy.init(args=args)
    node = Ros2Bridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        Sender.close_sender()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
