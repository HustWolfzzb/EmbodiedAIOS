import numpy as np
import mujoco
import os
from .ctrl_base import CtrlBase


class CtrlByMujoco(CtrlBase):
    ee_site_name = "ee_site"
    GRIPPER_OPEN_POS_7 = 0.0
    GRIPPER_CLOSE_POS_7 = 0.035
    GRIPPER_OPEN_POS_8 = 0.0
    GRIPPER_CLOSE_POS_8 = -0.035

    def __init__(
        self,
        sim_steps=10,
        render=False,
        model_path=os.path.abspath(
            os.path.join(
                "./src/piper_description", "mujoco_model", "piper_description.xml"
            )
        ),
    ):
        super().__init__()
        self.sim_steps = sim_steps

        self.model = mujoco.MjModel.from_xml_path(model_path)
        self.data = mujoco.MjData(self.model)
        self.actuator_ids = [
            mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, f"joint{i+1}")
            for i in range(self.joint_num)
        ]

        if render:
            self.renderer = mujoco.Renderer(self.model, height=480, width=640)
            self.cam = mujoco.MjvCamera()
            # 视距，拉远看整个机械臂
            self.cam.distance = 1.5

        # 两个夹爪的 ID
        self.joint7_id = mujoco.mj_name2id(
            self.model, mujoco.mjtObj.mjOBJ_JOINT, "joint7"
        )
        self.joint8_id = mujoco.mj_name2id(
            self.model, mujoco.mjtObj.mjOBJ_JOINT, "joint8"
        )

    def reset(self):
        mujoco.mj_resetData(self.model, self.data)

    def send_a_step(self):
        for _ in range(self.sim_steps):
            mujoco.mj_step(self.model, self.data)

    def set_joint(self, joint_id2positions: dict[str, float]) -> dict[str, float]:
        """
        返回超出关节限制的量
        """
        excess = {}
        for idx, (joint_id, position) in enumerate(joint_id2positions.items()):
            if joint_id in self.actuator_ids:
                # note: 直接修改qpos但不修改ctrl，相当于让关节瞬移到目标位置
                # 但仿真器又仿真ctrl它回到原点，所以每步step都几乎没动
                # self.data.qpos[:JOINT_NUM] = qpos
                self.data.ctrl[joint_id] = np.clip(
                    position,
                    self.joint_lower_limits[idx],
                    self.joint_upper_limits[idx],
                )
                excess[joint_id] = self.data.ctrl[joint_id] - position
            else:
                raise ValueError(f"Invalid joint ID: {joint_id}")
        return excess

    def add_joint(self, joint_id2action: dict[str, float]) -> dict[str, float]:
        """
        返回超出关节限制的量
        """
        excess = {}
        for idx, (joint_id, action) in enumerate(joint_id2action.items()):
            if joint_id in self.actuator_ids:
                new_qpos = self.data.qpos[joint_id] + action
                self.data.ctrl[joint_id] = np.clip(
                    new_qpos,
                    self.joint_lower_limits[idx],
                    self.joint_upper_limits[idx],
                )
                excess[joint_id] = self.data.ctrl[joint_id] - new_qpos
            else:
                raise ValueError(f"Invalid joint ID: {joint_id}")
        return excess

    def get_joint(self) -> np.ndarray:
        """
        不包括夹爪关节，单位: 弧度
        """
        return np.array([self.data.qpos[joint_id] for joint_id in self.actuator_ids])

    def get_ee_pos(self, site_name=None) -> np.ndarray:
        """
        单位: m
        """
        return np.array(
            self.data.site(site_name if site_name else self.ee_site_name).xpos.copy()
        )

    def get_ee_quat(self, site_name=None) -> np.ndarray:
        """
        获取末端执行器的姿态四元数，格式为 [w, x, y, z]（MuJoCo 默认格式）
        """
        rotmat = (
            self.data.site(site_name if site_name else self.ee_site_name)
            .xmat.reshape(3, 3)
            .copy()
        )
        ret = np.zeros(4)
        mujoco.mju_mat2Quat(ret, rotmat.reshape(9, -1))
        return ret

    def set_gripper(self, close: bool = True):
        """
        控制夹爪开合
        :param close: True表示闭合夹爪，False表示张开夹爪
        """
        if close:
            self.ctrl.set_joint(
                {
                    self.joint7_id: self.GRIPPER_CLOSE_POS_7,
                    self.joint8_id: self.GRIPPER_CLOSE_POS_8,
                }
            )
        else:
            self.ctrl.set_joint(
                {
                    self.joint7_id: self.GRIPPER_OPEN_POS_7,
                    self.joint8_id: self.GRIPPER_OPEN_POS_8,
                }
            )
        self.send_a_step()

    def render(self):
        if not hasattr(self, "renderer"):
            raise RuntimeError(
                "Renderer not initialized. Set render=True in constructor."
            )
        self.renderer.update_scene(self.data, camera=self.cam)
        return self.renderer.render()
