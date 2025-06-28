import numpy as np
import time
from piper_sdk import C_PiperInterface_V2
from ctrl_base import CtrlBase
from scipy.spatial.transform import Rotation as R


class CtrlByPiperSDK(CtrlBase):
    FACTOR = 1000.0

    def __init__(
        self,
        move_mode_end_pose: bool = False,
    ):
        """
        move_mode: int
        0: 末端位姿控制
        1: 关节角度控制
        """
        super().__init__()
        self.move_mode_end_pose = move_mode_end_pose
        self.actuator_ids = [i for i in range(self.joint_num)]
        # 统一是弧度
        self.joints_state_ctrl = np.zeros(self.joint_num, dtype=np.float32)

        self.piper = C_PiperInterface_V2("can0")
        self.piper.ConnectPort()
        self.piper.JointConfig(clear_err=0xAE)
        if not self._enable_fun():
            print(self.piper.GetArmStatus())
            raise RuntimeError("Failed to enable Piper arm.")
        self.reset(self.move_mode_end_pose)
        # print(self.piper.GetArmGripperMsgs())
        # print(self.piper.GetAllMotorAngleLimitMaxSpd())

    def __del__(self):
        """
        确保在对象销毁时复原并禁用机械臂
        """
        self.reset(move_mode_end_pose=False)
        print("Resetting Piper arm to initial state.")
        # time.sleep(2)
        self.disable()

    def reset(self, move_mode_end_pose: bool = None, timeout: int = 5):
        self.piper.JointConfig(clear_err=0xAE)
        self.piper.CrashProtectionConfig(0, 0, 0, 0, 0, 0)
        self.set_move_mode(move_mode_end_pose=False, timeout=timeout)
        self.piper.JointCtrl(0, 0, 0, 0, 0, 0)
        start = time.time()
        while True:
            status = self.piper.GetArmStatus()
            if status.arm_status.motion_status == 0x00:
                break
            if time.time() - start > timeout:
                raise TimeoutError("Failed to reset within the specified timeout.")
        self.set_gripper(close=False)

        if move_mode_end_pose is None:
            move_mode_end_pose = self.move_mode_end_pose
        else:
            self.move_mode_end_pose = move_mode_end_pose
        if move_mode_end_pose:
            self.set_move_mode(move_mode_end_pose=True, timeout=timeout)

    def send_a_step(self):
        if self.move_mode_end_pose:
            raise RuntimeError(
                "Cannot send a step in end-effector pose control mode. Please switch to joint control mode by reset(False)."
            )
        ctrl = np.degrees(self.joints_state_ctrl) * self.FACTOR
        self.piper.JointCtrl(
            joint_1=int(ctrl[0]),
            joint_2=int(ctrl[1]),
            joint_3=int(ctrl[2]),
            joint_4=int(ctrl[3]),
            joint_5=int(ctrl[4]),
            joint_6=int(ctrl[5]),
        )

    def set_joint(self, joint_id2positions: dict[str, float]) -> dict[str, float]:
        excess = {}
        for idx, (joint_id, position) in enumerate(joint_id2positions.items()):
            if joint_id in self.actuator_ids:
                self.joints_state_ctrl[joint_id] = np.clip(
                    position,
                    self.joint_lower_limits[idx],
                    self.joint_upper_limits[idx],
                )
                excess[joint_id] = self.joints_state_ctrl[joint_id] - position
            else:
                raise ValueError(f"Invalid joint ID: {joint_id}")
        return excess

    def add_joint(self, joint_id2action: dict[str, float]) -> dict[str, float]:
        excess = {}
        self.joints_state_ctrl = self.get_joint()
        for idx, (joint_id, action) in enumerate(joint_id2action.items()):
            if joint_id in self.actuator_ids:
                new_qpos = self.joints_state_ctrl[joint_id] + action
                self.joints_state_ctrl[joint_id] = np.clip(
                    new_qpos,
                    self.joint_lower_limits[idx],
                    self.joint_upper_limits[idx],
                )
                excess[joint_id] = self.joints_state_ctrl[joint_id] - new_qpos
            else:
                raise ValueError(f"Invalid joint ID: {joint_id}")
        return excess

    def get_joint(self) -> np.ndarray:
        joints = self.piper.GetArmJointMsgs()
        return np.radians(
            np.array(
                [
                    joints.joint_state.joint_1,
                    joints.joint_state.joint_2,
                    joints.joint_state.joint_3,
                    joints.joint_state.joint_4,
                    joints.joint_state.joint_5,
                    joints.joint_state.joint_6,
                ],
                dtype=np.float32,
            )
            / self.FACTOR
        )

    def get_gripper(self) -> float:
        gripper_msgs = self.piper.GetArmGripperMsgs()
        return gripper_msgs.gripper_state.grippers_angle / self.FACTOR / 1000.0

    def get_ee_pos(self) -> np.ndarray:
        end_pose = self.piper.GetArmEndPoseMsgs().end_pose
        return (
            np.array(
                [end_pose.X_axis, end_pose.Y_axis, end_pose.Z_axis],
                dtype=np.float32,
            )
            / self.FACTOR
            / 1000.0
        )

    def get_ee_quat(self) -> np.ndarray:
        end_pose = self.piper.GetArmEndPoseMsgs().end_pose
        return R.from_euler(
            "zyx",
            np.array([end_pose.RX_axis, end_pose.RY_axis, end_pose.RZ_axis])
            / self.FACTOR,
            degrees=True,
        ).as_quat()

    def set_ee_pose(
        self, position: list[float], euler_angles: list[float], timeout: int = 5
    ):
        """
        设置末端执行器位置和姿态
        :param position: 末端执行器位置 [x, y, z] 单位为米
        :param euler_angles: 欧拉角 [roll, pitch, yaw] 单位为度
        """
        if self.move_mode_end_pose is False:
            raise RuntimeError(
                "Cannot set end-effector pose in joint control mode. Please switch to end pose control mode by reset(True)."
            )
        position = np.array(position) * self.FACTOR * 1000.0
        euler_angles = np.array(euler_angles) * self.FACTOR
        self.piper.EndPoseCtrl(
            X=int(position[0]),
            Y=int(position[1]),
            Z=int(position[2]),
            RX=int(euler_angles[0]),
            RY=int(euler_angles[1]),
            RZ=int(euler_angles[2]),
        )

        start = time.time()
        while True:
            if self.piper.GetArmStatus().arm_status.motion_status == 0x00:
                print("End-effector pose set successfully.")
                break
            if time.time() - start > timeout:
                print("Failed to set end-effector pose within the specified timeout.")
                break

    def set_gripper(self, close: bool = True):
        # 50 mm
        self.piper.GripperCtrl(
            0 if close else int(100 * self.FACTOR),
            gripper_effort=1000,
            gripper_code=0x01,
            set_zero=0,
        )

    def render(self):
        raise RuntimeError("Rendering is not supported in Piper SDK control mode.")

    def _enable_fun(self) -> bool:
        """
        使能机械臂并检测使能状态,尝试5s,如果使能超时则返回False
        """
        enable_flag = False
        # 设置超时时间（秒）
        timeout = 5
        # 记录进入循环前的时间
        start_time = time.time()
        elapsed_time_flag = False
        while not (enable_flag):
            elapsed_time = time.time() - start_time
            print("--------------------")
            self.piper.EnableArm(7)
            msgs = self.piper.GetArmLowSpdInfoMsgs()
            enable_flag = (
                msgs.motor_1.foc_status.driver_enable_status
                and msgs.motor_2.foc_status.driver_enable_status
                and msgs.motor_3.foc_status.driver_enable_status
                and msgs.motor_4.foc_status.driver_enable_status
                and msgs.motor_5.foc_status.driver_enable_status
                and msgs.motor_6.foc_status.driver_enable_status
            )
            print("使能状态:", enable_flag)
            print("--------------------")
            # 检查是否超过超时时间
            if elapsed_time > timeout:
                print("超时....")
                elapsed_time_flag = True
                # enable_flag = True
                break
            time.sleep(1)
        if elapsed_time_flag:
            print("程序自动使能超时")
        return enable_flag

    def disable(self):
        """
        禁用机械臂
        """
        self.piper.DisableArm()
        self.piper.GripperCtrl(0, 1000, 0x02, 0)
        self.piper.DisconnectPort()
        print("Piper arm disabled.")

    def set_move_mode(self, move_mode_end_pose: bool, timeout: int = 5):
        """
        切换到末端执行器位姿控制模式
        :param timeout: 超时时间（秒）
        """
        start = time.time()
        # TODO: 看看mit模式是什么，据说响应速度更快
        self.piper.MotionCtrl_2(
            ctrl_mode=0x01,
            move_mode=0x0 if move_mode_end_pose else 0x01,
            move_spd_rate_ctrl=100,
            is_mit_mode=0x00,
        )
        while True:
            status = self.piper.GetArmStatus()
            if status.arm_status.mode_feed == (0x00 if move_mode_end_pose else 0x01):
                print(
                    "Switched move mode to "
                    + ("end pose control." if move_mode_end_pose else "joint control.")
                )
                break
            if time.time() - start > timeout:
                raise TimeoutError(
                    "Failed to switch move mode within the specified timeout."
                )


if __name__ == "__main__":
    piper_ctrl = CtrlByPiperSDK()
    time.sleep(1)
    print("Initial joint positions:", piper_ctrl.get_joint())
    print("Initial gripper position:", piper_ctrl.get_gripper())
    print("Initial end-effector position:", piper_ctrl.get_ee_pos())
    print("Initial end-effector orientation (quaternion):", piper_ctrl.get_ee_quat())
    # piper_ctrl.set_joint(
    #     {i: [0.5, 0.5, -0.7, 0.3, -0.2, 0.5, 0.08][i] for i in range(6)}
    # )
    # piper_ctrl.send_a_step()
    # print("Updated joint positions:", piper_ctrl.get_joint())
    # print("Updated gripper position:", piper_ctrl.get_gripper())
    # print("Updated end-effector position:", piper_ctrl.get_ee_pos())
    # print("Updated end-effector orientation (quaternion):", piper_ctrl.get_ee_quat())
    # piper_ctrl.set_gripper(close=True)
    # print("Gripper closed.")
    # time.sleep(1)
    # piper_ctrl.set_gripper(close=False)
    # print("Gripper opened.")
    # piper_ctrl.set_joint({i: [0.0, 0.0, -0.0, 0.0, 0.2, 0.0, 0.0][i] for i in range(6)})
    # piper_ctrl.send_a_step()
    # time.sleep(1)

    piper_ctrl.reset(move_mode_end_pose=True)
    piper_ctrl.set_ee_pose(
        position=[0.3, 0.2, 0.2],
        euler_angles=[0.0, 170.0, 0.0],
    )
    print("Set end-effector pose.")
    # time.sleep(1)
    print(piper_ctrl.piper.GetArmStatus().arm_status)
    print("Updated end-effector position:", piper_ctrl.get_ee_pos())
    print("Updated end-effector orientation (quaternion):", piper_ctrl.get_ee_quat())

    # 这两句不sleep好像到不了
    piper_ctrl.set_ee_pose(
        position=[0.3, 0.2, 0.2],
        euler_angles=[0.0, 170.0, 60.0],
    )
    piper_ctrl.set_ee_pose(
        position=[0.3, 0.2, 0.3],
        euler_angles=[0.0, 120.0, 60.0],
    )

    del piper_ctrl  # 确保在测试结束时销毁对象
