[中文文档](./README.md) | [English Document](./README_EN.md)

# YOLO_ROS2

基于YOLOV5 的ROS2封装，允许用户使用给定的模型文件和相机参数进行三维空间物体检测和抓取操作。

![YOLO_ROS2](https://img-blog.csdnimg.cn/592a90f1441f4a3ab4b94891878fbc55.png)

## 1. 安装依赖

首先，确保您已经更新了系统并且安装了必要的依赖。以下是一些安装步骤，其中`$ROS_DISTRO` 是您的ROS2发行版（例如：`foxy`、`galactic`）：

```bash
sudo apt update
sudo apt install python3-pip ros-$ROS_DISTRO-vision-msgs
pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple yolov5  
```

编译后，首先运行相机节点：
```
 ros2 launch orbbec_camera dabai_dcw.launch.py depth_registration:=true enable_d2c_viewer:=true
```
打开depth_registration和enable_d2c_viewer，会使发布的深度图像与RGB图像自动对齐。

之后运行Yolo_ROS2节点。默认情况下，它将使用CPU来进行检测。您可以根据需要更改这些参数：

```bash
ros2 run piper_vision yolo_detect_3d --ros-args -p device:=cpu -p interest:="bottle" -p pub_result_img:=True  
```
相机会探测interest指定的物体，比如bottle、person、all等，all表示所有物体都会被探测。然后发出相机坐标系下的坐标到话题`/camera_target_point`，单位为米。同时会在话题`/result_img`发布带有box的检测图像，可以通过rviz2查看。