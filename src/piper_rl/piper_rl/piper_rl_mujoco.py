import gymnasium as gym
import numpy as np
import mujoco
from mujoco import viewer
import os
from ament_index_python.packages import get_package_share_directory

JOINT_NUM = 6
JOINTLOWERLIMIT = [-np.pi] * JOINT_NUM
JOINTUPPERLIMIT = [np.pi] * JOINT_NUM


class MujocoRobotEnv(gym.Env):
    def __init__(self, sim_steps=5, render_mode=None, log_interval=1024):
        self.log_interval = log_interval
        pkg_share_dir = get_package_share_directory("piper_description")
        model_path = os.path.join(
            pkg_share_dir, "mujoco_model", "piper_description.xml"
        )
        model_path = os.path.abspath(model_path)
        self.model = mujoco.MjModel.from_xml_path(model_path)
        self.data = mujoco.MjData(self.model)

        self.render_mode = render_mode
        if self.render_mode:
            self.renderer = mujoco.Renderer(self.model)

        self.sim_steps = sim_steps
        self.step_counter = 0

        self.ee_site_name = "ee_site"
        self.target_pos = np.array([0.5, 0.0, 0.5], dtype=np.float32)

        # 动作空间：6个关节增量 + 1个夹爪开闭指令
        self.action_space = gym.spaces.Box(
            low=np.array([-0.1] * JOINT_NUM + [0.0], dtype=np.float32),
            high=np.array([0.1] * JOINT_NUM + [1.0], dtype=np.float32),
            dtype=np.float32,
        )

        # 观测空间：6个关节角度 + ee位置(xyz) + 目标点(xyz)
        self.observation_space = gym.spaces.Box(
            low=np.array(JOINTLOWERLIMIT + [-np.inf] * 6, dtype=np.float32),
            high=np.array(JOINTUPPERLIMIT + [np.inf] * 6, dtype=np.float32),
            dtype=np.float32,
        )

    def _get_obs(self):
        joint_angles = self.data.qpos[:JOINT_NUM].copy()
        ee_pos = self.data.site(self.ee_site_name).xpos.copy()
        return np.concatenate([joint_angles, ee_pos, self.target_pos]).astype(
            np.float32
        )

    def reset(self, seed=None, options=None):
        mujoco.mj_resetData(self.model, self.data)
        self.step_counter = 0
        # 可选：设置目标随机化
        # self.target_pos = np.random.uniform(low=[0.2, -0.2, 0.15], high=[0.4, 0.2, 0.25])
        return self._get_obs(), {}

    def step(self, action):
        self.step_counter += 1

        # 限制动作范围（安全起见）
        action = np.clip(action, self.action_space.low, self.action_space.high)

        # 当前角度 + 增量
        qpos = self.data.qpos[:JOINT_NUM].copy()
        qpos += action[:JOINT_NUM]
        qpos = np.clip(qpos, JOINTLOWERLIMIT, JOINTUPPERLIMIT)
        self.data.qpos[:JOINT_NUM] = qpos

        # 控制夹爪（第7维），0=张开，1=闭合（假设在 qpos[6] 上控制）
        if self.model.nq > JOINT_NUM:
            self.data.qpos[JOINT_NUM] = 0.04 if action[JOINT_NUM] > 0.5 else 0.0

        for _ in range(self.sim_steps):
            mujoco.mj_step(self.model, self.data)

        obs = self._get_obs()

        # 奖励函数：末端越接近目标越好
        ee_pos = obs[JOINT_NUM : JOINT_NUM + 3]
        dist = np.linalg.norm(ee_pos - self.target_pos)
        # dist(0 ~ 2) -> reward(20.09 ~ 0.0)
        reward = np.exp(-5.0 * dist + 3.0)
        if dist < 0.05:
            reward += 20.0
        if dist < 0.02:
            reward += 50.0
            print("已接近目标点")
            if self.data.qpos[JOINT_NUM] > 0.5:
                reward += 100.0
                done = True
            else:
                done = False
        else:
            done = False
        if self.step_counter % self.log_interval == 0:
            print(
                f"\n"
                + f"🤖 当前步数: {self.step_counter}\n"
                + f"📍 末端位置: x={ee_pos[0]:.3f}, y={ee_pos[1]:.3f}, z={ee_pos[2]:.3f}\n"
                + f"🎯 目标点:  x={self.target_pos[0]:.3f}, y={self.target_pos[1]:.3f}, z={self.target_pos[2]:.3f}\n"
                + f"📏 当前距离: {dist:.4f} m\n"
                + f'🤖 当前关节: {[f"{i:.3f}" for i in obs[:JOINT_NUM]]}\n'
                + f"💰 当前奖励: {reward:.4f}\n"
                + f"{'✅ 成功抓取!' if done else ''}"
            )
        return obs, reward, done, False, {}

    def render(self):
        print("渲染中...")
        if self.render_mode == "rgb_array":
            self.renderer.update_scene(self.data)
            return self.renderer.render()
        elif self.render_mode == "human":
            if not hasattr(self, "viewer"):
                self.viewer = mujoco.viewer.launch_passive(self.model, self.data)
            self.viewer.sync()
        else:
            raise ValueError("Invalid render mode. Use 'rgb_array' or 'human'.")
