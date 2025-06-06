[中文文档](./README.md) | [English Document](./README_EN.md)

# piper_vision使用说明

该包使用[yoloe](https://docs.ultralytics.com/models/yoloe/#introduction)算法，实现对物体的识别和位置定位。

## 1. 安装依赖

首先，确保您已经更新了系统并且安装了必要的依赖。以下是一些安装步骤，其中`$ROS_DISTRO` 是您的ROS2发行版（例如：`foxy`、`galactic`）：

```bash
sudo apt update
sudo apt install python3-pip ros-$ROS_DISTRO-vision-msgs
pip install -U ultralytics # 务必保证ultralytics处于最新版
```

然后从[这里](https://docs.ultralytics.com/models/yoloe/#available-models-supported-tasks-and-operating-modes)下载想要的模型，并保存到src/piper_vision/config/目录下。

## 2. 运行节点

编译后，首先运行相机节点：

```
 ros2 launch orbbec_camera dabai_dcw.launch.py depth_registration:=true enable_d2c_viewer:=true
```

> 打开depth_registration和enable_d2c_viewer，会使发布的深度图像与RGB图像自动对齐。发布出来的图像分辨率均为640*480。

之后运行Yolo_ROS2节点。您可以根据需要更改这些参数：

```bash
ros2 run tf2_ros static_transform_publisher   0.3 0 0.1   -1.5708 0 -1.5708   base_link camera_link

ros2 run piper_vision yolo_detect_3d --ros-args -p device:=cuda:0 -p interest:="person" -p depth_threshold:=15.0 -p model:=yoloe-11l-seg-pf -p bg_removal:=False -p target_frame_id:=map
```

- **`device:=cuda:0`**:

  指定计算设备，默认为 `cpu`。这里设置为 `cuda:0`，表示使用第一个 GPU 进行计算。如果使用 CPU，可以设置为 `cpu`。

- **`interest:="person"`**:

  指定要定位位置的目标对象，默认为 `"bottle"`。这里设置为 `"person"`，表示检测场景中的“人”。你可以根据需要更改为其他目标，如 `"bottle"`、`"cup"` 等。被检测到的对象会从话题`/piper_vision/target_point`发布。

- **`depth_threshold:=15.0`**:

  设置深度阈值，单位为米，默认为 `2.0`。超过深度阈值的物体会被视为背景，背景会在yolo进行推理前从图片中被移除。该参数仅在 `bg_removal` 为 `True` 时有效。

- **`model:=yoloe-11l-seg-pf`**:

  指定使用的 YOLO 模型，默认为 `"yoloe-11l-seg-pf"`。这里使用 `"yoloe-11l-seg-pf"` 模型进行目标检测和分割。你可以根据需要选择其他模型。

- **`bg_removal:=False`**:

  是否启用背景移除功能，默认为 `True`。这里设置为 `False`，表示不进行背景移除。如果设置为 `True`，系统会根据 `depth_threshold` 移除背景。

- **`conf_threshold:=0.7`**:
  设置置信度阈值，默认为 `0.7`。检测到的目标物体的置信度低于该值时，会被过滤掉，不会发布到话题中。可以根据需要调整该值以平衡检测精度和召回率。

- **`target_frame_id:=map`**:
  设置坐标转换的目标坐标系，用于`/piper_vision/all_object_points`。

yolo_ros2节点会在以下的topic中发布消息：

- `/piper_vision/all_object_points` 用于发布看到的所有目标物体的位置（相对于target_frame_id的坐标）和尺寸信息。
- `/piper_vision/target_point` 仅发布名为参数`interest`的目标物体的位置和尺寸信息。
- `/piper_vision/pred_image` 用于发布经过 YOLO 检测和标注后的图像，便于可视化检测结果。可以用rviz2查看。

## 3. 有关yoloe的介绍

yoloe的[论文](https://arxiv.org/html/2503.07465v1)介绍：

> In light of these, in this paper, we introduce YOLOE(ye), a highly **efficient**, **unified**, and **open** object detection and segmentation model, like human eye, under different prompt mechanisms, like texts, visual inputs, and prompt-free paradigm.

简单来说，使用yoloe可以识别更多的物体，还可以用text prompt指定识别图片中的哪个物体。目前我们可以用到两种模型，对应的模型请到这里[下载](https://docs.ultralytics.com/models/yoloe/#introduction)：

1. prompt-free yoloe

YOLOE also includes prompt-free variants that come with a built-in vocabulary. These models don't require any prompts and work like traditional YOLO models. Instead of relying on user-provided labels or visual examples, they detect objects from a [predefined list of 4,585 classes](https://github.com/xinyu1205/recognize-anything/blob/main/ram/data/ram_tag_list.txt) based on the tag set used by the [Recognize Anything Model Plus (RAM++)](https://arxiv.org/abs/2310.15200).

2. Text prompt

Text prompts allow you to specify the classes that you wish to detect through textual descriptions. The following code shows how you can use YOLOE to detect people and buses in an image.

## 4. 语义地图构建指引
运行流程：

在启动yolo_detect_3d节点侯，先运行vlm节点：

```
ros2 run piper_vision vlm_mapper_node
```

在命令行执行，这样会建图，地图会保存在./map/map.json下：

```
ros2 service call /piper_vision/map_capture std_srvs/srv/Empty "{}"
```
在piper_vision下的piper_vision_api.py有 get_coordinate_by_name函数，供侯老师调用。


