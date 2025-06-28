from scipy.spatial import KDTree
import os
import struct
import math
import pickle
import numpy as np
from scipy.spatial.transform import Rotation as R


class TableDrivenControl:
    """
    Table-driven control for a robotic arm using precomputed table
    to get joint angles from specified ee.
    """

    def __init__(
        self,
        wrist_distance: float = 0.091,  # defined in the description file
        anthropomorphic_table_path: str = os.path.join(
            os.path.dirname(__file__), "anthropomorphic.kdtree"
        ),
        wrist_table_path: str = os.path.join(os.path.dirname(__file__), "wrist.kdtree"),
    ):
        """
        Initializes the TableDrivenControl with a control table.
        Anthropomorphic Table Format:
        - KDTree with wrist positions as points.
        - Each point has a tuple of (rotvec, joint_angles) where:
            - rotvec: Rotation vector for the end effector.
            - joint_angles: Joint angles for the anthropomorphic part.
        Wrist Table Format:
        - KDTree with relative wrist rotation vectors as points.
        - Each point has joint angles for the wrist part.
        """
        self.wrist_distance = wrist_distance

        assert os.path.exists(
            anthropomorphic_table_path
        ), "Anthropomorphic table KDTree file not found."
        print(f"Loading anthropomorphic table KDTree from {anthropomorphic_table_path}")
        with open(anthropomorphic_table_path, "rb") as f:
            self.anthropomorphic_table, self.anthropomorphic_ee_rotvec_joint_angles = (
                pickle.load(f)
            )

        assert self.anthropomorphic_table.n == len(
            self.anthropomorphic_ee_rotvec_joint_angles
        ), "KDTree size does not match the number of joint angle entries."
        print("Anthropomorphic table loaded successfully.")

        assert os.path.exists(wrist_table_path), "Wrist table KDTree file not found."
        print(f"Loading wrist table KDTree from {wrist_table_path}")
        with open(wrist_table_path, "rb") as f:
            self.wrist_table, self.wrist_joint_angles = pickle.load(f)

        assert self.wrist_table.n == len(
            self.wrist_joint_angles
        ), "Wrist KDTree size does not match the number of joint angle entries."
        print("Wrist table loaded successfully.")

    def get_control_action(self, ee_pos, ee_quat=None, ee_euler=None):
        """
        Get the control action based on the end effector position and quat angles.

        Args:
            ee_pos (list): End effector position [x, y, z].
            ee_quat (list): End effector quaternion angles [w, x, y, z].
            ee_euler (list): End effector euler angles [roll, pitch, yaw].
            ee_quat and ee_euler are mutually exclusive.

        Returns:
            np.ndarray: Joint angles for the anthropomorphic part and wrist part.
        """
        xor = (ee_quat is None) ^ (ee_euler is None)
        assert xor, "Either ee_quat or ee_euler must be provided, but not both."
        if ee_euler is not None:
            ee_quat = R.from_euler("zyx", ee_euler, degrees=False).as_quat()

        # Calc the wrist pos. Default wrist direction vector is [0, 0, 1]
        wrist_pos = np.array(ee_pos, dtype=np.float32) - R.from_quat(ee_quat).apply(
            [0.0, 0.0, self.wrist_distance]
        ).astype(np.float32)

        # Find the nearest attitude and joint angles for the anthropomorphic part
        dist, idx = self.anthropomorphic_table.query(wrist_pos)
        if dist > 0.1:
            print(f"Warning: Anthropomorphic distance {dist:.4f} is too large.")
        anthropomorphic_rotvec, anthropomorphic_joint_angles = (
            self.anthropomorphic_ee_rotvec_joint_angles[idx]
        )
        print(f"Anthropomorphic rotvec: {anthropomorphic_rotvec}")
        print(
            f"Anthropomorphic vector: {R.from_rotvec(anthropomorphic_rotvec).apply([0, 0, 1])}"
        )

        anthropomorphic_ctrl = CtrlByMujoco(
            model_path="/home/xujinyang/ros/EmbodiedAIOS/src/piper_description/mujoco_model/piper_no_gripper_anthropomorphic_description.xml",
            render=True,
        )
        anthropomorphic_ctrl.reset()
        anthropomorphic_ctrl.data.qpos[:3] = anthropomorphic_joint_angles
        mujoco.mj_forward(anthropomorphic_ctrl.model, anthropomorphic_ctrl.data)
        Image.fromarray(anthropomorphic_ctrl.render()).save(
            os.path.join(os.path.dirname(__file__), "anthropomorphic.png")
        )
        rotvec = R.from_matrix(
            anthropomorphic_ctrl.data.site("ee_site").xmat.reshape(3, 3)
        )
        print(rotvec.apply([0, 0, 1]))
        print(rotvec.as_rotvec())
        anthropomorphic_rotvec = rotvec.as_rotvec()

        # Calc relative attitude of the wrist part
        relative_wrist_rotvec = (
            R.from_quat(ee_quat)
            * (
                R.from_quat([0.707105, 0.707108, 0, 0])  # wrist default rotation,不确定
                * R.from_rotvec(anthropomorphic_rotvec)
            ).inv()
        ).as_rotvec()
        print(f"Relative wrist rotation vector: {relative_wrist_rotvec}")
        print(
            f"Relative wrist vector: {R.from_rotvec(relative_wrist_rotvec).apply([0, 0, self.wrist_distance])}"
        )

        # Find the nearest joint angles for the wrist part
        dist, wrist_idx = self.wrist_table.query(relative_wrist_rotvec)
        if dist > 0.1:
            print(f"Warning: Wrist distance {dist:.4f} is too large.")
        wrist_joint_angles = self.wrist_joint_angles[wrist_idx]

        wrist_ctrl = CtrlByMujoco(
            model_path="/home/xujinyang/ros/EmbodiedAIOS/src/piper_description/mujoco_model/piper_no_gripper_wrist_description.xml",
            render=True,
        )
        wrist_ctrl.reset()
        wrist_ctrl.data.qpos[:3] = [0, 0, 0]
        mujoco.mj_forward(wrist_ctrl.model, wrist_ctrl.data)
        Image.fromarray(wrist_ctrl.render()).save(
            os.path.join(os.path.dirname(__file__), "wrist.png")
        )
        rotvec = R.from_matrix(wrist_ctrl.data.site("ee_site").xmat.reshape(3, 3))
        print(rotvec.apply([0, 0, self.wrist_distance]))
        print(rotvec.as_rotvec())
        # print(wrist_ctrl.data.site("ee_site").xpos)

        # wrist_joint_angles = np.array([0, 0.9, 3.1415], dtype=np.float32)
        # wrist_joint_angles = np.array([0, 0, 0], dtype=np.float32)

        return np.concat((anthropomorphic_joint_angles, wrist_joint_angles))


if __name__ == "__main__":
    import sys

    sys.path.append(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    from piper_control.piper_control.ctrl_by_mujoco import CtrlByMujoco
    import mujoco
    from PIL import Image

    # Example usage
    # 需要 export MUJOCO_GL=egl
    controller = CtrlByMujoco(render=True)
    table_control = TableDrivenControl()
    controller.reset()
    mujoco.mj_forward(controller.model, controller.data)
    img = controller.render()
    img = Image.fromarray(img)
    img.save(os.path.join(os.path.dirname(__file__), "init.png"))
    print("Initial Joints:", controller.data.qpos[: controller.joint_num])
    print("End Effector Position:", controller.get_ee_pos())
    print("End Effector euler:", R.from_quat(controller.get_ee_quat()).as_euler("zyx"))
    joints = table_control.get_control_action(
        ee_pos=[0.0, 0.0, 0.5],
        ee_euler=[0.0, 2 * np.pi / 4, 0.0],
    )
    print("Calculated Joint Angles:", joints)
    controller.data.qpos[: controller.joint_num] = joints
    mujoco.mj_forward(controller.model, controller.data)
    print("End Effector Position:", controller.get_ee_pos())
    print("End Effector euler:", R.from_quat(controller.get_ee_quat()).as_euler("zyx"))
    print("End Effector rotvec:", R.from_quat(controller.get_ee_quat()).as_rotvec())
    print("Wrist pos: ", controller.data.site("anthropomorphic_arm").xpos)
    img = controller.render()
    img = Image.fromarray(img)
    img.save(os.path.join(os.path.dirname(__file__), "moved.png"))
