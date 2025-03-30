import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import PointStamped
import cv2
from cv_bridge import CvBridge
import numpy as np

class YoloDepthDetector(Node):
    def __init__(self):
        super().__init__('yolo_depth_node')
        self.bridge = CvBridge()
        self.color_img = None
        self.depth_img = None

        # 加载YOLO
        self.net = cv2.dnn.readNet("yolov3.weights", "yolov3.cfg")
        self.classes = open("coco.names").read().strip().split("\n")
        self.pub = self.create_publisher(PointStamped, "/camera_target_point", 10)

        self.create_subscription(Image, "/camera/color/image_raw", self.color_cb, 10)
        self.create_subscription(Image, "/camera/depth/image_raw", self.depth_cb, 10)

    def color_cb(self, msg):
        self.color_img = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        self.try_detect()

    def depth_cb(self, msg):
        self.depth_img = self.bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")

    def try_detect(self):
        if self.color_img is None or self.depth_img is None:
            return

        blob = cv2.dnn.blobFromImage(self.color_img, 1/255.0, (416, 416), swapRB=True, crop=False)
        self.net.setInput(blob)
        layer_outputs = self.net.forward(self.net.getUnconnectedOutLayersNames())

        h, w = self.color_img.shape[:2]
        for out in layer_outputs:
            for det in out:
                scores = det[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if confidence > 0.5 and self.classes[class_id] == "cup":
                    center_x = int(det[0] * w)
                    center_y = int(det[1] * h)
                    depth = self.depth_img[center_y, center_x] / 1000.0

                    pt = PointStamped()
                    pt.header.frame_id = "camera_link"
                    pt.header.stamp = self.get_clock().now().to_msg()
                    pt.point.x = depth
                    pt.point.y = 0.0
                    pt.point.z = 0.0
                    self.pub.publish(pt)
                    self.get_logger().info(f"🎯 发布3D目标点: x={depth}")
                    return

def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(YoloDepthDetector())
    rclpy.shutdown()


