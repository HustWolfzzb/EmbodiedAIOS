from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from piper_msgs.action import GripperControl
from rclpy.action import ActionServer
from rclpy.node import Node
import rclpy
from sensor_msgs.msg import JointState
import time


class GripperControllerNode(Node):
    def __init__(self):
        super().__init__('gripper_controller_node')

        self._action_server = ActionServer(
            self,
            GripperControl,
            'gripper_control',
            self.execute_callback
        )

        self.gripper_pub = self.create_publisher(JointTrajectory, '/gripper_controller/joint_trajectory', 3)
        # self.arm_pub = self.create_publisher(JointTrajectory, '/arm_controller/joint_trajectory', 3)

        # 当前 joint 状态缓存
        self.current_joint_state = None
        self.create_subscription(JointState, '/joint_states', self.joint_state_callback, 3)


        self.get_logger().info("🎯 Gripper Action Server 已启动")


    def joint_state_callback(self, msg):
        """订阅 joint_states 并缓存当前值"""
        self.current_joint_state = msg


    def execute_callback(self, goal_handle):
        angle = goal_handle.request.gripper_angle  # joint6
        width = goal_handle.request.gripper_width  # joint7

        # ✅ 安全保护
        if not (-0.785 <= angle <= 0.785):
            goal_handle.abort()
            return GripperControl.Result(success=False, message="gripper_angle 超出范围 (-0.785 ~ 0.785)")

        if not (0.005 <= width <= 0.07):
            goal_handle.abort()
            return GripperControl.Result(success=False, message="gripper_width 超出范围 (0.01 ~ 0.04)")

        # self.get_logger().info(f"🌀 控制 joint6 旋转至 {angle:.6f} rad")


        # timeout = 5.0  # 最多等待 5 秒
        # start_time = time.time()
        # while rclpy.ok() and self.current_joint_state is None:
        #     rclpy.spin_once(self, timeout_sec=0.1)
        #     if time.time() - start_time > timeout:
        #         goal_handle.abort()
        #         return GripperControl.Result(success=False, message="❌ 等待 joint_states 超时")
       
        # # 构造 joint1~6 的当前值列表
        # joint_map = dict(zip(self.current_joint_state.name, self.current_joint_state.position))
        # joint_names = ['joint1', 'joint2', 'joint3', 'joint4', 'joint5', 'joint6']
        # joint_positions = []
        # print(joint_map)

        # for name in joint_names:
        #     if name == 'joint6':
        #         joint_positions.append(angle)  # 目标角度
        #     else:
        #         pos = joint_map.get(name)
        #         if pos is None:
        #             goal_handle.abort()
        #             return GripperControl.Result(success=False, message=f"❌ 缺失 {name} 状态")
        #         joint_positions.append(pos)

        # # ✅ 发布 joint1~6 的完整轨迹（只修改 joint6）
        # traj_joint6 = JointTrajectory()
        # traj_joint6.joint_names = joint_names
        # point6 = JointTrajectoryPoint()
        # point6.positions = joint_positions
        # point6.time_from_start.sec = 1
        # traj_joint6.points.append(point6)
        # self.arm_pub.publish(traj_joint6)
        # print(traj_joint6)

        self.get_logger().info(f"🤏 控制 joint7 开合宽度为 {width:.3f} m")

        # ✅ 控制 joint7（夹爪）→ gripper_controller
        traj_joint7 = JointTrajectory()
        traj_joint7.joint_names = ['joint7']
        point7 = JointTrajectoryPoint()
        point7.positions = [width]
        point7.time_from_start.sec = 1
        traj_joint7.points.append(point7)
        self.gripper_pub.publish(traj_joint7)

        goal_handle.succeed()
        return GripperControl.Result(success=True, message="✅ 控制成功")


def main(args=None):
    rclpy.init(args=args)
    node = GripperControllerNode()
    rclpy.spin(node)
    rclpy.shutdown()
