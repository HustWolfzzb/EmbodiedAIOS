import rclpy
from sensor_msgs.msg import JointState
from geometry_msgs.msg import PointStamped
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

import numpy as np


class CtrlByROS:
    def __init__(self):
        super().__init__()
        self.current_joint_states = None
        rclpy.init(args=None)
        self.node = rclpy.create_node("my_robot_rl_env")
        self.node.create_subscription(
            JointState, "/joint_states", self.joint_state_cb, 10
        )
        self.arm_pub = self.node.create_publisher(
            JointTrajectory, "/arm_controller/joint_trajectory", 10
        )
        self.gripper_pub = self.node.create_publisher(
            JointTrajectory, "/gripper_controller/joint_trajectory", 10
        )

    def joint_state_cb(self, msg):
        name2index = {name: i for i, name in enumerate(msg.name)}
        new_joint = [
            msg.position[name2index[f"joint{i+1}"]] for i in range(self.joint_num)
        ]
        self.current_joint_states = new_joint

    def get_current_joint(self):
        if self.current_joint_states is None:
            raise ValueError("Joint states not received yet.")
        return np.array(self.current_joint_states)

    def send_arm_trajectory(self, joint_positions):
        msg = JointTrajectory()
        msg.joint_names = [f"joint{i+1}" for i in range(self.joint_num)]
        point = JointTrajectoryPoint()
        point.positions = joint_positions
        point.time_from_start.sec = 1
        point.time_from_start.nanosec = 0
        msg.points.append(point)
        self.arm_pub.publish(msg)

    def send_gripper_trajectory(self, gripper_position):
        msg = JointTrajectory()
        msg.joint_names = ["gripper_joint"]
        point = JointTrajectoryPoint()
        point.positions = [gripper_position]
        point.time_from_start.sec = 1
        point.time_from_start.nanosec = 0
        msg.points.append(point)
        self.gripper_pub.publish(msg)
