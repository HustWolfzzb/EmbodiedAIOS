from math import frexp
from traceback import print_tb
from torch import imag
from yolov5 import YOLOv5
import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory
from rcl_interfaces.msg import ParameterDescriptor
from vision_msgs.msg import Detection2DArray, ObjectHypothesisWithPose, Detection2D
from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge
import cv2
import yaml
from piper_vision.cv_tool import px2xy
import os
# from geometry_msgs.msg import PointStamped
from piper_msgs.msg import ObjectPos
from piper_msgs.srv import SetInterest
import message_filters
import queue
from rclpy.callback_groups import ReentrantCallbackGroup
import time
import threading
from std_srvs.srv import SetBool
import numpy as np
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup

# Get the ROS distribution version and set the shared directory for YoloV5 configuration files.
ros_distribution = os.environ.get("ROS_DISTRO")
package_share_directory = get_package_share_directory('piper_vision')

# Create a ROS 2 Node class YoloV5Ros2.
class YoloV5Ros2(Node):
    def __init__(self):
        super().__init__('yolov5_ros2')
        self.get_logger().info(f"Current ROS 2 distribution: {ros_distribution}")

        # Declare ROS parameters.
        self.declare_parameter("device", "cuda", ParameterDescriptor(
            name="device", description="Compute device selection, default: cpu, options: cuda:0"))

        self.declare_parameter("model", "yolov5s", ParameterDescriptor(
            name="model", description="Default model selection: yolov5s"))

        # self.declare_parameter("image_topic", "/image_raw", ParameterDescriptor(
        #     name="image_topic", description="Image topic, default: /image_raw"))
        
        self.declare_parameter("camera_info_topic", "/camera/color/camera_info", ParameterDescriptor(
            name="camera_info_topic", description="Camera information topic, default: /camera/color/camera_info"))

        # Read parameters from the camera_info topic if available, otherwise, use the file-defined parameters.
        self.declare_parameter("camera_info_file", f"{package_share_directory}/config/camera_info.yaml", ParameterDescriptor(
            name="camera_info", description=f"Camera information file path, default: {package_share_directory}/config/camera_info.yaml"))

        # Default to displaying detection results.
        self.declare_parameter("show_result", False, ParameterDescriptor(
            name="show_result", description="Whether to display detection results, default: False"))

        # Default to publishing detection result images.
        self.declare_parameter("pub_result_img", False, ParameterDescriptor(
            name="pub_result_img", description="Whether to publish detection result images, default: False"))

        
        self.declare_parameter("interest", "bottle", ParameterDescriptor(
            name="interest", description="The object to detect, default: bottle"))
        
        # 1. Load the model.
        model_path = package_share_directory + "/config/" + self.get_parameter('model').value + ".pt"
        device = self.get_parameter('device').value
        self.yolov5 = YOLOv5(model_path=model_path, device=device)

        # 2. Create publishers.
        self.yolo_result_pub = self.create_publisher(
            Detection2DArray, "yolo_result", 10)
        
        self.camera_target_point_pub = self.create_publisher(ObjectPos, "/camera_target_point", 10)
        
        self.result_msg = Detection2DArray()

        self.result_img_pub = self.create_publisher(Image, "result_img", 10)

        # 3. Create an image subscriber (subscribe to depth information for 3D cameras, load camera info for 2D cameras).
        # image_topic = self.get_parameter('image_topic').value
        # self.image_sub = self.create_subscription(
        #     Image, image_topic, self.image_callback, 10)
        self.image_queue = queue.Queue(maxsize=2)

        rgb_sub = message_filters.Subscriber(self, Image, '/camera/color/image_raw')
        depth_sub = message_filters.Subscriber(self, Image, '/camera/depth/image_raw')
        info_sub = message_filters.Subscriber(self, CameraInfo, '/camera/depth/camera_info')


        # 同步时间戳, 时间允许有误差在0.03s
        sync = message_filters.ApproximateTimeSynchronizer([rgb_sub, depth_sub, info_sub], 3, 0.02)
        sync.registerCallback(self.multi_callback) #执行反馈函数

        camera_info_topic = self.get_parameter('camera_info_topic').value
        self.camera_info_sub = self.create_subscription(
            CameraInfo, camera_info_topic, self.camera_info_callback, 1)

        # Get camera information.
        with open(self.get_parameter('camera_info_file').value) as f:
            self.camera_info = yaml.full_load(f.read())
            self.get_logger().info(f"default_camera_info: {self.camera_info['k']} \n {self.camera_info['d']}")

        # 4. Image format conversion (using cv_bridge).
        self.bridge = CvBridge()

        self.show_result = self.get_parameter('show_result').value
        self.pub_result_img = self.get_parameter('pub_result_img').value
        self.interest = self.get_parameter('interest').value

        self.client = self.create_client(SetBool, '/camera/set_ldp_enable')
        self.interest_srv = self.create_service(SetInterest, '/set_interest', self.interest_callback)
        # Exclusive callback group can ensure that only one callback is executed at a time
        # timer_cb_group = MutuallyExclusiveCallbackGroup()
        threading.Thread(target=self.yolo_main, daemon=True).start()
        # self.timer = self.create_timer(0.1, self.yolo_main, callback_group=timer_cb_group)

        self.get_logger().info("YoloV5Ros2 node init.")

    def interest_callback(self, request, response):
        self.interest = request.interest
        response.success = True
        self.get_logger().info(f"object detect interest changed to {self.interest}")
        return response

    def send_request(self, client, msg):
        future = client.call_async(msg)
        while rclpy.ok():
            if future.done() and future.result():
                return future.result()
            
    def multi_callback(self, ros_rgb_image, ros_depth_image, depth_camera_info):
        if self.image_queue.full():
            self.image_queue.get()
        self.image_queue.put((ros_rgb_image, ros_depth_image, depth_camera_info))

    def camera_info_callback(self, msg: CameraInfo):
        """
        Get camera parameters through a callback function.
        """
        self.camera_info['k'] = msg.k
        self.camera_info['p'] = msg.p
        self.camera_info['d'] = msg.d
        self.camera_info['r'] = msg.r
        self.camera_info['roi'] = msg.roi

        self.destroy_subscription(self.camera_info_sub)
    def yolo_main(self):
        while rclpy.ok():
            try:
                ros_rgb_image, ros_depth_image, depth_camera_info = self.image_queue.get(block=True, timeout=1)
            except queue.Empty:
                self.get_logger().error("image_queue is empty")
                return
            try:
                self.image_proc(ros_rgb_image, ros_depth_image, depth_camera_info)
            except Exception as e:
                self.get_logger().error('yolo_main:' + str(e))
            time.sleep(0.2)
                
    def image_proc(self, ros_rgb_image: Image, ros_depth_image: Image, depth_camera_info: CameraInfo):
        # 5. Detect and publish results.
        rgb_image = np.ndarray(shape=(ros_rgb_image.height, ros_rgb_image.width, 3), dtype=np.uint8, buffer=ros_rgb_image.data)
        depth_image = np.ndarray(shape=(ros_depth_image.height, ros_depth_image.width), dtype=np.uint16, buffer=ros_depth_image.data)
        result_image = np.copy(rgb_image)
        rgb_h, rgb_w = rgb_image.shape[:2]
        h, w = depth_image.shape[:2]
        depth = np.copy(depth_image).reshape((-1, ))
        depth[depth<=0] = 55555

        image = self.bridge.imgmsg_to_cv2(ros_rgb_image)
        detect_result = self.yolov5.predict(image)

        self.get_logger().debug(str(detect_result))

        object_pos = ObjectPos()
        # point_stamp = PointStamped()
        
        object_pos.point_stamp.header.frame_id = "camera"
        object_pos.point_stamp.header.stamp = self.get_clock().now().to_msg()

        # self.result_msg.detections.clear()
        # self.result_msg.header.frame_id = "camera"
        # self.result_msg.header.stamp = self.get_clock().now().to_msg()

        # Parse the results.
        predictions = detect_result.pred[0]
        boxes = predictions[:, :4]  # x1, y1, x2, y2
        scores = predictions[:, 4]
        categories = predictions[:, 5]

        for index in range(len(categories)):
            name = detect_result.names[int(categories[index])]
            self.get_logger().debug("image_proc: find " + name)

            if name != self.interest and self.interest != "all": 
                continue
            
            # detection2d = Detection2D()
            # detection2d.id = name
            # TODO: 判断x和y是否超过了h,w
            x1, y1, x2, y2 = boxes[index]
            # x1 = int(x1) if int(x1) > 0 else 0
            # y1 = int(y1) if int(y1) > 0 else 0
            # x2 = int(x2) if int(x2) < w else w
            # y2 = int(y2) if int(y2) < h else h
            x1 = int(x1)
            y1 = int(y1) 
            x2 = int(x2) 
            y2 = int(y2) 
            center_x = (x1+x2)/2.0
            center_y = (y1+y2)/2.0
            d_center_x = center_x
            d_center_y = center_y
            if d_center_y < 0 : d_center_y = 0
            roi_distance = depth_image[y1:y2, x1:x2]
            try:
                ave_dist = round(float(np.mean(roi_distance[np.logical_and(roi_distance>0, roi_distance<10000)])/1000.0), 3)
                # dist_xy1 = round(float(depth_image[y1, x1]/1000.0), 3) if 0 < depth_image[y1, x1] <= 10000 else 1.0
                # dist_xy2 = round(float(depth_image[y2, x2]/1000.0), 3) if 0 < depth_image[y2, x2] <= 10000 else 1.0

            except BaseException as e:
                self.get_logger().error('error2: ' + str(e))
                txt = "DISTANCE ERROR !!!"
                return
            if np.isnan(ave_dist):
                txt = "DISTANCE ERROR !!!"
                return
            
            dist = float(depth_image[int(d_center_y),int(d_center_x)])/1000.0

            # px2xy
            world_x, world_y = px2xy(
                [center_x, center_y], self.camera_info["k"], self.camera_info["d"], ave_dist)
            self.get_logger().debug(f"depth camera height:{h}, width:{w}; rgb camera height:{rgb_h}, width:{rgb_w}")
            self.get_logger().debug(f"object position: x:{x1}, {x2}, y:{y1}, {y2}, ave_dist:{ave_dist}, central_dist:{dist};;" + 
                                   f"world_x:{world_x}, world_y:{world_y}")

            # 因为相机的坐标系跟机械臂的坐标系设置还不一样，所以需要转换一下：
            object_pos.point_stamp.point.x = dist
            object_pos.point_stamp.point.y = -world_x
            object_pos.point_stamp.point.z = -world_y
            # 计算物体宽和高
            world_x1, world_y1 = px2xy(
                [x1, y1], self.camera_info["k"], self.camera_info["d"], dist)
            world_x2, world_y2 = px2xy(
                [x2, y2], self.camera_info["k"], self.camera_info["d"], dist)

            object_pos.object_width = abs(world_x2 - world_x1)
            object_pos.object_height = abs(world_y2 - world_y1)

            self.get_logger().debug(f"Object width: {object_pos.object_width:.2f}, height: {object_pos.object_height:.2f}")

            # Draw results.
            if self.show_result or self.pub_result_img:
                cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(image, f"{name}({world_x:.2f},{world_y:.2f})", (x1, y1),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                cv2.waitKey(1)
            # print('==========', point_stamp)
            object_pos.point_stamp.header.frame_id = "camera_link"  # ✅ 改这里

            self.camera_target_point_pub.publish(object_pos)
            # 只要检测到一个物体，就退出循环
            break

        # Display results if needed.
        if self.show_result:
            cv2.imshow('result', image)
            cv2.waitKey(1)

        # Publish result images if needed.
        if self.pub_result_img:
            result_img_msg = self.bridge.cv2_to_imgmsg(image, encoding="bgr8")
            result_img_msg.header = ros_rgb_image.header
            self.result_img_pub.publish(result_img_msg)

        # if len(categories) > 0:
        #     self.yolo_result_pub.publish(self.result_msg)

def main():
    rclpy.init()
    rclpy.spin(YoloV5Ros2())
    rclpy.shutdown()

if __name__ == "__main__":
    main()
