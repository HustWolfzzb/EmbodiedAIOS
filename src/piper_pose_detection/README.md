# 🦾 `piper_pose_detection` 模块说明文档

> **功能**：识别合适的夹爪抓取位姿。接收目标图像（包含深度信息，通常由视觉系统等提供），输出合适的抓取位姿。

## GraspNet

### 安装

见https://github.com/graspnet/graspnet-baseline的README.md。

拉取submodule后将logs/目录放到graspnet_baseline/目录下。

需要nvcc编译，注意cuda版本要求。在cuda12.2，torch2.5.1+cu121复现成功。

### demo

见graspnet_baseline/demo.py。

模型输入：
- RGB图像
- 深度图像
- 深度相机参数：主点（光心）的像素坐标、焦距（像以素为单位）
- 工作空间掩码（可选）：只识别工作空间的物体

模型输出：
- 识别到的每个夹爪的分数、宽高深、坐标、旋转矩阵

通常是按分数排序，最高的几个夹爪就是有效夹爪位姿
