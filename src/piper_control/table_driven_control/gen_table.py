import sys
import mujoco
import os
import numpy as np
import itertools
from multiprocessing import Pool, cpu_count, Process, Manager
from scipy.spatial import KDTree
from scipy.spatial.transform import Rotation as R
import pickle

# from queue import

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
from piper_control.piper_control.ctrl_by_mujoco import CtrlByMujoco


# 步长，弧度
STRIDE = 1 / 180 * np.pi
anthropomorphic_site_name = "anthropomorphic_arm"
lower = CtrlByMujoco.joint_lower_limits
upper = CtrlByMujoco.joint_upper_limits


def sim_a_range(joint_1, lower, upper, anthropomorphic, result_queue):
    # print(f"Processing Joint 1: {joint_1}, Anthropomorphic: {anthropomorphic}")
    ctrl = CtrlByMujoco(
        sim_steps=10,
        model_path=os.path.abspath(
            os.path.join(
                "./src/piper_description",
                "mujoco_model",
                (
                    "piper_no_gripper_anthropomorphic_description.xml"
                    if anthropomorphic
                    else "piper_no_gripper_wrist_description.xml"
                ),
            ),
        ),
    )
    ctrl.reset()
    ranges = [np.arange(l, u, STRIDE) for l, u in zip(lower, upper)]
    combinations = itertools.product(*ranges)
    for idx, c in enumerate(combinations):
        ctrl.data.qpos[:] = [joint_1, c[0], c[1]]
        mujoco.mj_forward(ctrl.model, ctrl.data)
        # print(joints)
        # print(ee_pos, ee_quat)
        result_queue.put(
            {
                "joints": ctrl.get_joint()[:3],
                "ee_pos": ctrl.get_ee_pos(),
                "ee_quat": ctrl.get_ee_quat(),
            }
        )
    return f"Joint 1: {joint_1}, Anthropomorphic: {anthropomorphic}, Completed!"


def collect_results(result):
    print(result)


def build_kdtree(result_queue, filename, anthropomorphic):
    li = []
    kdtree_li = []
    while True:
        result = result_queue.get()
        if result is None:
            break
        if anthropomorphic:
            li.append(
                (
                    R.from_quat(result["ee_quat"]).as_rotvec().astype(np.float32),
                    result["joints"],
                )
            )
            kdtree_li.append(result["ee_pos"])
        else:
            li.append(result["joints"])
            kdtree_li.append(
                R.from_quat(result["ee_quat"]).as_rotvec().astype(np.float32)
            )

    print("\nBuilding KDTree...")
    kdtree = KDTree(np.array(kdtree_li, dtype=np.float32))
    li = np.array(li, dtype=np.float32)
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), filename),
        "wb",
    ) as f:
        pickle.dump((kdtree, li), f)
    print(f"KDTree built with {len(kdtree_li)} points.")

    # with open(
    #     os.path.join(
    #         os.path.dirname(os.path.abspath(__file__)),
    #         filename.replace(".kdtree", ".txt"),
    #     ),
    #     "w",
    # ) as f:
    #     for item_1, item_2 in zip(kdtree_li, li):
    #         f.write(f"{item_1.tolist()} {item_2.tolist()}\n")


def main():
    print("cpu_count:", cpu_count())
    with Manager() as manager:
        p = Pool(cpu_count())
        # p = Pool(1)
        result_queue = manager.Queue()
        for joint_1 in np.arange(lower[0], upper[0], STRIDE):
            p.apply_async(
                sim_a_range,
                args=(joint_1, lower[1:3], upper[1:3], True, result_queue),
                callback=collect_results,
                error_callback=lambda e: print(f"Error: {e}"),
            )

        p.close()
        pro = Process(
            target=build_kdtree,
            args=(result_queue, "anthropomorphic.kdtree", True),
        )
        pro.start()
        p.join()
        result_queue.put(None)  # Signal the writer to stop
        pro.join()

    with Manager() as manager:
        p = Pool(cpu_count())
        result_queue = manager.Queue()
        for joint_4 in np.arange(lower[3], upper[3], STRIDE * 10):
            p.apply_async(
                sim_a_range,
                args=(joint_4, lower[4:6], upper[4:6], False, result_queue),
                callback=collect_results,
                error_callback=lambda e: print(f"Error: {e}"),
            )

        p.close()
        pro = Process(
            target=build_kdtree,
            args=(result_queue, "wrist.kdtree", False),
        )
        pro.start()
        p.join()
        result_queue.put(None)  # Signal the writer to stop
        pro.join()


if __name__ == "__main__":
    main()
