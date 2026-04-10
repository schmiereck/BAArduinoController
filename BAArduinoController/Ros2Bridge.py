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

        # Aktuelle Gelenkwinkel (in Radiant) — nur durch Arduino-Feedback aktualisiert
        self._current_positions = [1.5708, 0.0, 0.0, 3.14, 1.5708, 0.76]

        # Ziel-Positionen fuer Paketberechnung (nicht-aktive Joints)
        self._target_positions = list(self._current_positions)

        # JointState Publisher
        self._joint_state_publisher = self.create_publisher(
            JointState, '/joint_states', 10)

        # Timer: publiziert joint_states 10x pro Sekunde
        self._timer = self.create_timer(0.1, self.publish_joint_states)

        # Action Server: Arm (joint_0–4)
        self._action_server = ActionServer(
            self,
            FollowJointTrajectory,
            '/arm_controller/follow_joint_trajectory',
            execute_callback=self.execute_callback_arm,
            cancel_callback=self.cancel_callback
        )

        # Action Server: Greifer (joint_5)
        self._gripper_action_server = ActionServer(
            self,
            FollowJointTrajectory,
            '/gripper_controller/follow_joint_trajectory',
            execute_callback=self.execute_callback_gripper,
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

    async def _execute_trajectory(self, goal_handle, active_joints):
        """Gemeinsamer Handler fuer arm_controller und gripper_controller.
        active_joints: Liste der Joints, die diese Trajektorie enthaelt.
        Joints ausserhalb dieser Liste behalten ihre aktuelle Position."""
        trajectory = goal_handle.request.trajectory
        joint_names = trajectory.joint_names
        points = trajectory.points

        if not points:
            goal_handle.succeed()
            return FollowJointTrajectory.Result()

        self.get_logger().info(f'Empfange Trajektorie mit {len(points)} Punkten fuer: {active_joints}')

        name_to_ros_idx = {name: i for i, name in enumerate(joint_names)}
        all_joints = ['joint_0', 'joint_1', 'joint_2', 'joint_3', 'joint_4', 'joint_5']

        # --- Phase 1: Alle Punkte an den Arduino senden ---
        for i, point in enumerate(points):
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                return FollowJointTrajectory.Result()

            # _target_positions fuer aktive Joints aktualisieren,
            # damit parallel laufende Trajektorien (arm/gripper) die
            # Zielwerte lesen statt veralteter Positionen.
            # _current_positions wird NUR durch Arduino-Feedback aktualisiert.
            for joint_name in active_joints:
                if joint_name in name_to_ros_idx:
                    servo_idx = all_joints.index(joint_name)
                    self._target_positions[servo_idx] = point.positions[name_to_ros_idx[joint_name]]

            # Servo-Winkel aus _target_positions ableiten
            angles_deg = [
                self.map_ros_to_servo(idx, self._target_positions[idx])
                for idx in range(len(all_joints))
            ]

            if i == 0:
                duration_ms = 200
            else:
                prev_point = points[i-1]
                diff = (point.time_from_start.sec - prev_point.time_from_start.sec) + \
                    (point.time_from_start.nanosec - prev_point.time_from_start.nanosec) * 1e-9
                duration_ms = max(20, int(diff * 1000))

            Sender.send_binary_packet(angles_deg, duration_ms)

            # Auf Arduino-Pufferplatz warten (blockierend, verhindert
            # Paket-Interleaving mit paralleler Trajektorie)
            wait_start = time.time()
            while time.time() - wait_start < 5.0:
                resp = Sender.read_response()
                if resp is None:
                    time.sleep(0.01)
                    continue  # Weiter warten, nicht abbrechen
                free_slots = resp.get('free_slots', 20)
                # Position-Reports waehrend Phase 1 auch auswerten
                if resp.get('type') == 'position':
                    self._update_from_report(resp)
                if free_slots > 1:
                    break
                time.sleep(0.01)

        # --- Phase 2: Auf Arduino-Feedback warten (echte Servo-Positionen) ---
        self.get_logger().info(
            f'Warte auf Arduino-Feedback (Bewegung laeuft)...')

        TIMEOUT = 60.0  # Sicherheits-Timeout
        start_time = time.time()

        while time.time() - start_time < TIMEOUT:
            if goal_handle.is_cancel_requested:
                Sender.send_flush()
                goal_handle.canceled()
                return FollowJointTrajectory.Result()

            resp = Sender.read_response()
            if resp is not None and resp.get('type') == 'position':
                self._update_from_report(resp)
                # Arduino meldet idle -> Bewegung fertig
                if not resp.get('is_active', True):
                    break

            time.sleep(0.05)
        else:
            self.get_logger().warn('Timeout beim Warten auf Arduino-Feedback!')

        goal_handle.succeed()
        self.get_logger().info('Trajektorie erfolgreich ausgefuehrt.')
        return FollowJointTrajectory.Result()

    async def execute_callback_arm(self, goal_handle):
        """Arm-Controller: joint_0 bis joint_4."""
        return await self._execute_trajectory(
            goal_handle,
            ['joint_0', 'joint_1', 'joint_2', 'joint_3', 'joint_4']
        )

    async def execute_callback_gripper(self, goal_handle):
        """Greifer-Controller: joint_5."""
        return await self._execute_trajectory(goal_handle, ['joint_5'])

    async def execute_callback(self, goal_handle):
        """Legacy: alle 6 Joints."""
        return await self._execute_trajectory(
            goal_handle,
            ['joint_0', 'joint_1', 'joint_2', 'joint_3', 'joint_4', 'joint_5']
        )

    async def execute_callback_old(self, goal_handle):
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

    def _update_from_report(self, report):
        """Aktualisiert _current_positions aus einem Arduino Position-Report.
        Wandelt Servo-Grad (0-180) zurueck in Radiant."""
        angles = report.get('angles', [])
        if len(angles) == 6:
            for i in range(6):
                self._current_positions[i] = angles[i] / 57.2958

    def map_ros_to_servo(self, joint_index, angle_rad):
        """Wandelt ROS-Radianten in Arduino-Servo-Grade um.

        Die URDF-Joints haben alle limit 0..3.14 rad, was direkt 0..180° Servo entspricht.
        Kein Offset nötig — die initial_positions kodieren die Home-Stellung bereits in rad.
        """
        angle_deg = angle_rad * 57.2958
        return int(round(max(0.0, min(180.0, angle_deg))))

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
