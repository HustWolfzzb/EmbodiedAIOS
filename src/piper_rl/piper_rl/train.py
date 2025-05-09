import os
import numpy as np
from gymnasium.wrappers import RecordVideo
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback
from piper_rl_gazebo_node import GazeboRobotEnv
from piper_rl_mujoco import MujocoRobotEnv
import time


def train():
    if args.gazebo:
        env = GazeboRobotEnv()
    else:
        if args.train_record:
            env = MujocoRobotEnv(render_mode="rgb_array")
            video_dir = "./videos/"
            env = RecordVideo(
                env, video_folder=video_dir, episode_trigger=lambda e: e % 100 == 0
            )
        else:
            env = MujocoRobotEnv()
    model = PPO(
        policy="MlpPolicy",
        env=env,
        policy_kwargs=dict(net_arch=[256, 128]),
        learning_rate=1e-3,
        batch_size=128,
        n_steps=1024,
        gamma=0.99,
        verbose=1,
        ent_coef=0.05,
        tensorboard_log="./ppo_logs/",
    )

    checkpoint_callback = CheckpointCallback(
        save_freq=100000, save_path="./ppo_models/", name_prefix="piper_rl"
    )

    model.learn(total_timesteps=1000 * 1000 * 100, callback=checkpoint_callback)

    model.save("ppo_piper_final")
    print("✅ 模型训练完成，已保存为 ppo_piper_final.zip")


def test():
    if args.gazebo:
        env = GazeboRobotEnv()
    else:
        env = MujocoRobotEnv()
    model = PPO.load("ppo_piper_final_maximize_z")
    obs = env.reset()
    for epoch in range(100000):
        # time.sleep(1)
        action, _ = model.predict(obs)
        obs, reward, done, _ = env.step(action)

        # print(f"epoch {epoch}, Reward:", reward)
        if done:
            print("🎉 成功抓取，重新开始")
            obs = env.reset()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="测试训练好的策略")
    parser.add_argument("--gazebo", action="store_true", help="使用mujoco仿真")
    parser.add_argument(
        "--train_record",
        action="store_true",
        help="训练时定时录制训练过程",
    )
    args = parser.parse_args()

    if args.test:
        test()
    else:
        train()
