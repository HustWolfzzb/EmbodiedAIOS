import os
import numpy as np
from gymnasium.wrappers import RecordVideo
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback
import time
from piper_rl import RobotEnv


def decay_schedule(initial_value):
    def func(progress_remaining):
        return initial_value * (progress_remaining)

    return func


def make_env(MyRobotEnv, ctrl_mode, worker_id):
    def _init():
        env = MyRobotEnv(ctrl_mode=ctrl_mode, worker_id=worker_id)
        return env

    return _init


def train():
    print("🚀 进程数:", args.proc)
    if args.proc > 1:
        if not args.ctrl_mode == "mujoco":
            raise ValueError("多进程仿真只支持 mujoco 模式")
        if args.record:
            raise ValueError("多进程仿真不支持录制视频，请设置 --record False")
        from stable_baselines3.common.vec_env import SubprocVecEnv

        env = SubprocVecEnv(
            [make_env(RobotEnv, args.ctrl_mode, i) for i in range(args.proc)],
            start_method="spawn",
        )
    else:
        if args.record:
            # 需要 export MUJOCO_GL=egl
            env = RobotEnv(ctrl_mode=args.ctrl_mode, render=True)
            video_dir = "./videos/"
            env = RecordVideo(
                env,
                video_folder=video_dir,
                episode_trigger=lambda e: e % 100 == 0,
                video_length=5000,
            )
        else:
            env = RobotEnv(ctrl_mode=args.ctrl_mode)
    model = PPO(
        policy="MlpPolicy",
        env=env,
        device="cpu",
        policy_kwargs=dict(
            net_arch=[256, 512, 512, 128],
            log_std_init=-2.0,
            ortho_init=True,
        ),
        # 在已训练好的模型基础上继续训练，需要调小学习率，如3e-5
        learning_rate=decay_schedule(3e-4),
        batch_size=1024,
        n_steps=2048,
        gamma=0.99,
        verbose=1,
        # 越高越鼓励探索，但不能太高，否则std会变大，策略会变得不稳定，一般1e-2以内
        ent_coef=1e-2,
        tensorboard_log="./ppo_logs/",
    )
    # model.set_parameters("ppo_piper_final.zip")

    checkpoint_callback = CheckpointCallback(
        save_freq=100000, save_path="./ppo_models/", name_prefix="piper_rl_checkpoint"
    )

    model.learn(total_timesteps=1000 * 1000 * 100, callback=checkpoint_callback)

    model.save("ppo_piper_final")
    print("✅ 模型训练完成，已保存为 ppo_piper_final.zip")


def test():
    if args.record:
        env = RobotEnv(ctrl_mode=args.ctrl_mode, render=True, log_interval=1)
        video_dir = "./videos/"
        env = RecordVideo(
            env,
            video_folder=video_dir,
            episode_trigger=lambda e: e % 1 == 0,
            video_length=5000,
        )
    else:
        env = RobotEnv(ctrl_mode=args.ctrl_mode, log_interval=1)
    model = PPO.load("ppo_piper_final")
    obs = env.reset()[0]
    for epoch in range(100000):
        action, _ = model.predict(obs)
        obs, reward, done, _, _ = env.step(action)

        print(f"epoch {epoch}, Reward:", reward)
        if done:
            print("🎉 成功抓取，重新开始")
            obs = env.reset()
        time.sleep(0.5)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="测试训练好的策略")
    parser.add_argument(
        "--ctrl_mode",
        choices=["mujoco", "ros", "piper_sdk"],
        default="mujoco",
        help="控制模式，使用mujoco仿真/ros/piper_sdk控制机械臂",
    )
    parser.add_argument(
        "--record",
        default=False,
        action="store_true",
        help="录制视频，默认True",
    )
    parser.add_argument("--proc", default=64, help="并行仿真进程数")
    args = parser.parse_args()
    if args.ctrl_mode == "ros":
        print("🚀 使用ros控制")
    elif args.ctrl_mode == "piper_sdk":
        print("🚀 使用Piper SDK控制")
    else:
        print("🚀 使用Mujoco仿真")

    if args.test:
        test()
    else:
        train()
