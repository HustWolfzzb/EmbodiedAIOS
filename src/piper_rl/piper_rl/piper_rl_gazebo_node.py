# 文件：piper_rl_node.py 中添加此类

import gym
import gym.spaces
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from geometry_msgs.msg import PointStamped
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
import time
import tf2_ros
from tf2_ros import TransformException
from geometry_msgs.msg import TransformStamped
from builtin_interfaces.msg import Time as RosTime

# 是否是最大化z轴高度任务
MAXMIZE_Z = True
JOINTLOWERLIMIT = [-np.pi, 0.0, -np.pi, -np.pi, -np.pi, -np.pi]
JOINTUPPERLIMIT = [np.pi, np.pi, 0.0, np.pi, np.pi, np.pi]
JOINT_NUM = len(JOINTLOWERLIMIT)  # 机械臂关节数
JOINT_MOVE_THRESHOLD = 0.1  # 关节运动阈值


class GazeboRobotEnv(gym.Env):
    def __init__(self):
        super(GazeboRobotEnv, self).__init__()
        self.step_cnt = 0
        self.log_interval = 1
        self.is_static = True
        rclpy.init(args=None)
        self.node = rclpy.create_node("my_robot_rl_env")

        # 初始状态（6个关节 + 目标点）
        self.current_joint_states = [0.0] * JOINT_NUM
        # 夹爪joint7
        self.gripper_close = False
        self.target_point = [0.5, 0.0, 0.5]

        # 订阅 joint_states 与 目标点
        self.node.create_subscription(
            JointState, "/joint_states", self.joint_state_cb, 10
        )
        self.node.create_subscription(
            PointStamped, "/base_target_point", self.target_cb, 10
        )
        self.arm_pub = self.node.create_publisher(
            JointTrajectory, "/arm_controller/joint_trajectory", 10
        )
        self.gripper_pub = self.node.create_publisher(
            JointTrajectory, "/gripper_controller/joint_trajectory", 10
        )

        # 动作空间：每个关节的角度范围 + 夹爪动作（0/1)
        # self.action_space = gym.spaces.Box(
        #     low=np.array(
        #         JOINTLOWERLIMIT, dtype=np.float32
        #     ),
        #     high=np.array(JOINTUPPERLIMIT, dtype=np.float32),
        #     dtype=np.float32,
        # )

        # 动作空间：每个关节的角度增量范围（-0.01 ~ 0.01 rad）+ 夹爪动作（0/1)
        self.action_space = gym.spaces.Box(
            low=np.array([-0.1] * JOINT_NUM + [0.0], dtype=np.float32),
            high=np.array([0.1] * JOINT_NUM + [1.0], dtype=np.float32),
            dtype=np.float32,
        )

        # 动作空间 Δx, Δy, Δz (单位米)，夹爪动作(0/1)
        # self.action_space = gym.spaces.Box(
        #     low=np.array([-0.02, -0.02, -0.02, 0]),
        #     high=np.array([0.02, 0.02, 0.02, 1]),
        #     dtype=np.float32,
        # )

        # 观测空间：6个关节的角度
        # self.observation_space = gym.spaces.Box(
        #     low=np.array(JOINTLOWERLIMIT, dtype=np.float32),
        #     high=np.array(JOINTUPPERLIMIT, dtype=np.float32),
        #     dtype=np.float32,
        # )

        # 观测空间：6个关节角度 + 当前点xyz + 目标点 xyz
        self.observation_space = gym.spaces.Box(
            low=np.array(JOINTLOWERLIMIT + [-np.inf] * 6),
            high=np.array(JOINTUPPERLIMIT + [np.inf] * 6),
            dtype=np.float32,
        )

        # 观测空间：当前点 xyz + 目标点 xyz
        # self.observation_space = gym.spaces.Box(
        #     low=-np.inf, high=np.inf, shape=(6,), dtype=np.float32
        # )
        # self.observation_space = gym.spaces.Box(
        #     low=-np.inf, high=np.inf, shape=(3,), dtype=np.float32
        # )
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self.node)

    def send_arm_goal(self, delta_xyz):
        # 末端当前位置
        # ee_pos = self.get_ee_pose()
        # target_pos = [ee_pos[0] + delta_xyz[0], ee_pos[1] + delta_xyz[1], ee_pos[2] + delta_xyz[2]]

        # 简化IK：只控制joint2, joint3, joint5（你可以加更复杂的IK）
        # 这里直接简单推 joint2，joint3来模拟z方向伸缩
        new_joint = self.current_joint_states.copy()
        # Example IK: adjust joint2 for z, joint1 for x,y（伪IK，真实需要更完善）
        new_joint[1] -= delta_xyz[2] * 5
        new_joint[0] += delta_xyz[1] * 5
        new_joint[2] += delta_xyz[0] * 5

        self.send_arm_joint_goal(new_joint)
        return np.clip(new_joint, JOINTLOWERLIMIT, JOINTUPPERLIMIT)

    def send_arm_joint(self, delta_joint):
        new_joint = self.current_joint_states.copy()
        for i in range(JOINT_NUM):
            new_joint[i] += delta_joint[i]
        # new_joint[5] = np.pi
        self.send_arm_joint_goal(new_joint)
        return np.clip(new_joint, JOINTLOWERLIMIT, JOINTUPPERLIMIT)

    def send_arm_joint_goal(self, target_joint):
        traj = JointTrajectory()
        traj.joint_names = [f"joint{i+1}" for i in range(JOINT_NUM)]
        point = JointTrajectoryPoint()
        point.positions = target_joint
        point.time_from_start.sec = 1
        traj.points.append(point)
        # self.current_joint_states = target_joint

        self.arm_pub.publish(traj)

    def joint_state_cb(self, msg):
        name2index = {name: i for i, name in enumerate(msg.name)}
        new_joint = [msg.position[name2index[f"joint{i+1}"]] for i in range(JOINT_NUM)]
        self.is_static = (
            np.linalg.norm(np.array(self.current_joint_states) - np.array(new_joint))
            < 1e-6
        )
        self.current_joint_states = new_joint

    def target_cb(self, msg):
        self.target_point = [msg.point.x, msg.point.y, msg.point.z]

    def joint_ready(self, target_joint) -> bool:
        # 判断关节是否到达目标位置：没超过阈值或没动
        return (
            np.linalg.norm(
                np.array(self.current_joint_states) - np.array(target_joint),
            )
            < JOINT_MOVE_THRESHOLD
            or self.is_static
        )

    def wait_for_joint_ready(self, target_joint, timeout_ms=1000):
        start_time = self.node.get_clock().now()
        while not self.joint_ready(target_joint):
            if (
                self.node.get_clock().now() - start_time
            ).nanoseconds > timeout_ms * 1e6:
                return False
            rclpy.spin_once(self.node, timeout_sec=0.1)
        return True

    # 获取当前末端执行器位置
    def get_ee_pose(self):
        try:
            latest_time = self.node.get_clock().now().to_msg()
            trans: TransformStamped = self.tf_buffer.lookup_transform(
                "base_link",  # target frame
                "gripper_base",  # source frame
                rclpy.time.Time(),  # ← 获取最近的可用变换
                timeout=rclpy.duration.Duration(seconds=1.0),
            )
            pos = trans.transform.translation
            return [pos.x, pos.y, pos.z]
        except TransformException as e:
            self.node.get_logger().warn(f"TF transform failed: {e}")
            return [0.0, 0.0, 0.0]

    def _get_obs(self):
        return np.array(
            self.current_joint_states + self.get_ee_pose() + self.target_point,
            dtype=np.float32,
        )

    def control_gripper(self, close=True):

        traj = JointTrajectory()
        traj.joint_names = ["joint7"]  # 夹爪

        point = JointTrajectoryPoint()
        point.positions = [0.0 if close else 0.02]  # 0.3 为闭合程度，按需调整
        point.time_from_start.sec = 1
        traj.points.append(point)

        self.gripper_pub.publish(traj)

        # 等待夹爪运动生效
        for _ in range(5):
            rclpy.spin_once(self.node, timeout_sec=0.25)

    def reset(self):
        # 机械臂复位
        self.send_arm_joint_goal([0.0] * JOINT_NUM)
        self.control_gripper(close=True)
        # 等待机械臂运动生效
        self.node.get_logger().info("机械臂复位中...")
        if not self.wait_for_joint_ready([0.0] * JOINT_NUM, 1000):
            self.node.get_logger().warn("机械臂复位超时")
        else:
            self.node.get_logger().info("机械臂复位成功")
        return self._get_obs()

    def step(self, action):
        reward = 0.0

        delta_joint = action[:JOINT_NUM].tolist()
        gripper_action = action[JOINT_NUM]
        new_joint = self.send_arm_joint(delta_joint)

        if gripper_action > 0.5:
            self.control_gripper(close=True)

        if not self.wait_for_joint_ready(new_joint, 1000):
            self.node.get_logger().info(f"关节运动超时,{new_joint}")
            reward -= 10.0

        obs = self._get_obs()
        ee_pos = self.get_ee_pose()
        goal_pos = self.target_point

        dist = np.linalg.norm(np.array(ee_pos) - np.array(goal_pos))

        # maximize z
        if MAXIMIZE_Z:
            joint = self.current_joint_states
            reward += (
                ee_pos[2] * 10
                - abs(joint[1] - np.pi / 2)
                - abs(joint[2] - (-np.pi))
                - abs(joint[4])
            )
            if ee_pos[2] < 0.2:
                reward -= 10.0
            if ee_pos[2] > 0.6:
                reward **= 2
            if ee_pos[2] > 0.7:
                done = True
            else:
                done = False
        else:
            # dist(0 ~ 2) -> reward(20.09 ~ 0.0)
            reward += np.exp(-5.0 * dist + 3.0)
            if dist < 0.05:
                reward += 20.0
            if dist < 0.02:
                reward += 50.0
                self.node.get_logger().info("已接近目标点")
                if gripper_action > 0.5:
                    reward += 100.0
                    done = True
                else:
                    done = False
            else:
                done = False
        # === 控制台输出：可视化当前状态 ===
        self.step_cnt += 1
        if self.step_cnt % self.log_interval == 0:
            self.node.get_logger().info(
                f"\n"
                + f"🤖 当前步数: {self.step_cnt}\n"
                + f"📍 末端位置: x={ee_pos[0]:.3f}, y={ee_pos[1]:.3f}, z={ee_pos[2]:.3f}\n"
                + f"🎯 目标点:  x={goal_pos[0]:.3f}, y={goal_pos[1]:.3f}, z={goal_pos[2]:.3f}\n"
                + f"📏 当前距离: {dist:.4f} m\n"
                + f'🤖 当前关节: {[f"{i:.2f}" for i in self.current_joint_states]}\n'
                + f"💰 当前奖励: {reward:.4f}\n"
                + f"{'✅ 成功抓取!' if done else ''}"
            )

        return obs, reward, done, {}

    # def forward_kinematics_estimate(self, joints):
    #     # 简化计算，用 joint1/joint2 的角度估个方向向量模拟末端位置
    #     x = 0.4 + 0.2 * np.cos(joints[0])
    #     y = 0.0 + 0.2 * np.sin(joints[0])
    #     z = 0.4 + 0.1 * np.sin(joints[1])
    #     return [x, y, z]


if __name__ == "__main__":
    env = MyRobotEnv()
    obs = env.reset()
    print("Start Obs:", obs)
    action = np.zeros(6)
    action[1] = 0.1  # 向下移动关节2试试
    obs, reward, done, _ = env.step(action)
    print("New Obs:", obs)
    print("Reward:", reward, "Done:", done)
    print("张开夹爪")
    env.control_gripper(close=False)
    time.sleep(1)
    print("闭合夹爪")
    env.control_gripper(close=True)
    pose = env.get_ee_pose()
    print("末端位姿:", pose)
