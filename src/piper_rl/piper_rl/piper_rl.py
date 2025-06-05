import gymnasium as gym
import numpy as np
import mujoco
import os
import cv2
import math
import random
import sys

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
from piper_control.piper_control.ctrl_by_mujoco import CtrlByMujoco
from piper_control.piper_control.ctrl_by_piper_sdk import CtrlByPiperSDK


class RobotEnv(gym.Env):
    def __init__(
        self,
        ctrl_mode: str,
        render=False,
        log_interval=1024,
        capture_interval=None,
        max_step=100000,
        worker_id=None,
    ):
        self.worker_id = worker_id
        self.log_interval = log_interval
        self.capture_interval = capture_interval
        self.max_step = max_step

        if ctrl_mode == "ros":
            raise NotImplementedError()
        elif ctrl_mode == "mujoco":
            self.ctrl = CtrlByMujoco(
                render=render,
            )
        elif ctrl_mode == "piper_sdk":
            self.ctrl = CtrlByPiperSDK()
        else:
            raise ValueError(f"Unsupported ctrl_mode: {ctrl_mode}")

        self.step_counter = 0
        self.total_reward = 0
        self.first_catch_step = -1
        self.reset_counter = 0
        self.mean_first_catch_step = 0

        self.set_target_pos()
        self.target_quat = gen_target_quat()

        # 动作空间：6个关节增量
        self.action_space = gym.spaces.Box(
            low=np.array(
                [-0.5] * (self.ctrl.joint_num - 1) + [-0.05], dtype=np.float32
            ),
            high=np.array([0.5] * (self.ctrl.joint_num - 1) + [0.05], dtype=np.float32),
            dtype=np.float32,
        )

        # 观测空间：6个关节角度 + ee位置(xyz) + 目标点(xyz) + ee姿态四元数 + 目标姿态四元数
        self.observation_space = gym.spaces.Box(
            low=np.array(
                self.ctrl.joint_lower_limits + [-np.inf] * 6 + [-1.0] * 8,
                dtype=np.float32,
            ),
            high=np.array(
                self.ctrl.joint_upper_limits + [np.inf] * 6 + [1.0] * 8,
                dtype=np.float32,
            ),
            dtype=np.float32,
        )

    def _get_obs(self):
        joint_angles = self.ctrl.get_joint()
        ee_pos = self.ctrl.get_ee_pos()
        ee_quat = self.ctrl.get_ee_quat()
        return np.concatenate(
            [
                joint_angles,
                ee_pos,
                self.target_pos,
                ee_quat,
                self.target_quat,
            ]
        ).astype(np.float32)

    def reset(self, seed=None, options=None):
        self.ctrl.reset()
        self.step_counter = 0
        self.total_reward = 0
        if self.first_catch_step != -1:
            self.mean_first_catch_step = (
                self.mean_first_catch_step * self.reset_counter + self.first_catch_step
            ) / (self.reset_counter + 1)
        self.first_catch_step = -1
        self.reset_counter += 1
        # 设置目标随机化
        self.set_target_pos()
        self.target_quat = gen_target_quat()
        return self._get_obs(), {}

    def ctrl_gripper(self, close=True):
        self.ctrl.set_gripper(close=close)

    def step(self, action):
        self.step_counter += 1

        # 限制动作范围（安全起见）
        # action = np.clip(action, self.action_space.low, self.action_space.high)

        reward = 0
        # 防止action过于接近边界，[0~0.5]->[0~9.7*6]惩罚力度
        reward -= np.sum(
            10000
            * np.abs(norm(action, self.action_space.low, self.action_space.high) - 0.5)
            ** 10
        )
        id2action = {
            actuator_id: action[idx]
            for idx, actuator_id in enumerate(self.ctrl.actuator_ids)
        }
        excess = self.ctrl.add_joint(id2action)
        # 关节限制惩罚，防止关节超过可转动范围
        reward -= 10.0 * np.sum(abs(np.array(list(excess.values()))))

        self.ctrl.send_a_step()

        ee_pos = self.ctrl.get_ee_pos()
        # 末端姿态四元数
        ee_quat = self.ctrl.get_ee_quat()
        dist = np.linalg.norm(ee_pos - self.target_pos)
        dir_dist = np.linalg.norm(ee_quat - self.target_quat)
        # dist(0 ~ 2) -> reward(20 ~ 0)
        reward += 2 * np.exp(-4.0 * (0.9 * dist + 0.1 * dir_dist) + 3.0)
        # dir_dist(0 ~ 2) -> reward(20 ~ 0)
        # 不拆成两个指数函数，防止一个距离较小时梯度很大，把另一个指数函数的梯度盖过去了
        # reward += np.exp(-4.0 * dir_dist + 3.0)
        catched = False
        # if dist < 0.1:
        #     # 越接近目标越鼓励小action
        #     reward -= np.linalg.norm(action[:JOINT_NUM]) / dist
        # 阈值定太大了容易鼓励瞎碰：来回动直到刚好碰到目标范围
        if dist < 0.02:
            reward += 100.0
        # if dir_dist < 0.1:
        #     reward += 100.0
        if dist < 0.02 and dir_dist < 0.1:
            # self.ctrl_gripper(close=True)
            # if float_equal(
            #     self.data.qpos[self.joint7_id], GRIPPER_CLOSE_POS_7
            # ) and float_equal(
            #     self.data.qpos[self.joint8_id], GRIPPER_CLOSE_POS_8
            # ):
            reward += 200.0
            catched = True
            if self.first_catch_step == -1:
                self.first_catch_step = self.step_counter
        if self.capture_interval and (
            self.step_counter % self.capture_interval == 0 or catched
        ):
            cv2.imwrite(f"videos/{self.step_counter}.png", self.render())
        # reward -= self.step_counter / self.max_step * 100.0
        # deleted: 训练其即使到达目标点也不停止，要在max_step内最大化奖励，鼓励其一直留在目标点附近
        if self.step_counter >= self.max_step:
            done = True
            # reward -= 50.0
        else:
            done = False
        self.total_reward += reward
        if (
            (self.worker_id == 0 or self.worker_id == None)
            and (self.step_counter % self.log_interval == 0 or done)
            or catched
        ):
            print(
                f"\n"
                + f"🤖 当前步数: {self.step_counter}\n"
                + f"📍 末端/目标位置: ({list2str(ee_pos)})/({list2str(self.target_pos)})\n"
                + f"📏 当前距离: {dist:.4f} m\n"
                + f"🤖 当前action: ({list2str(action)})\n"
                + f"🤖 当前关节: ({list2str(self.ctrl.get_joint())})\n"
                + f"🤖 姿态四元数之差: ({list2str(ee_quat-self.target_quat)})\n"
                + f"💰 当前/总奖励: {reward:.4f} / {self.total_reward:.4f}, 步均奖励: {self.total_reward/self.step_counter:.4f}\n"
                + (f"✅ 成功抓取! \n" if catched else "")
                # + (
                #     f"第{self.first_catch_step}步首次抓取\n"
                #     if self.first_catch_step != -1
                #     else ""
                # )
                + (f"❌ 达到最大步数{self.max_step}\n" if done else "")
                + f"🤖 reset次数: {self.reset_counter}, 平均首次抓取所需步数: {self.mean_first_catch_step:.4f}\n"
            )
        return self._get_obs(), reward, catched or done, False, {}

    def render(self):
        return self.ctrl.render()

    def set_target_pos(self):
        # self.target_pos = np.random.uniform(low=[0.2, -0.2, 0.2], high=[0.3, 0.2, 0.4])
        self.target_pos = np.array((0.287, 0.015, 0.304))

        # # 获取三个 joint 的 qpos 索引
        # x_id = self.model.jnt_qposadr[
        #     mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, "target_x")
        # ]
        # y_id = self.model.jnt_qposadr[
        #     mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, "target_y")
        # ]
        # z_id = self.model.jnt_qposadr[
        #     mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, "target_z")
        # ]

        # # 设置位置（单位：米）
        # self.data.qpos[x_id] = self.target_pos[0]
        # self.data.qpos[y_id] = self.target_pos[1]
        # self.data.qpos[z_id] = self.target_pos[2]

        # # 推进仿真使 site 更新
        # mujoco.mj_forward(self.model, self.data)


def float_equal(a, b, epsilon=1e-4):
    return abs(a - b) < epsilon


def gen_target_quat():
    """
    均匀随机生成一个单位四元数，格式为 [w, x, y, z]，符合 MuJoCo 使用格式
    """
    # u1, u2, u3 = np.random.uniform(size=3)

    # q1 = np.sqrt(1 - u1) * np.sin(2 * np.pi * u2)
    # q2 = np.sqrt(1 - u1) * np.cos(2 * np.pi * u2)
    # q3 = np.sqrt(u1) * np.sin(2 * np.pi * u3)
    # q4 = np.sqrt(u1) * np.cos(2 * np.pi * u3)

    # # 返回格式为 [w, x, y, z]（MuJoCo 默认格式）
    # return np.array([q4, q1, q2, q3])
    return np.array([0.5, 0.1, 0.4, 0.76])


def norm(a, low, high):
    return (a - low) / (high - low)


def list2str(data, precision=3):
    """
    将输入的 list 或一维 ndarray 中的每个元素转换为保留指定有效位数的字符串。

    参数:
        data (list 或 np.ndarray): 输入数据。
        precision (int): 指定保留的有效位数。

    返回:
        list: 包含保留指定有效位数的字符串的列表。
    """
    if not isinstance(data, (list, np.ndarray)):
        raise TypeError("输入必须是 list 或一维 ndarray")

    if isinstance(data, np.ndarray) and data.ndim != 1:
        raise ValueError("输入的 ndarray 必须是一维的")

    # 转换为字符串，保留指定有效位数
    result = [f"{x:.{precision}f}" for x in data]
    return ", ".join(result)
