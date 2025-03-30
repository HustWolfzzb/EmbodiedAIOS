import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PointStamped
import tf2_ros
import tf2_geometry_msgs

class TFTransformer(Node):
    def __init__(self):
        super().__init__('tf_transformer')
        self.buffer = tf2_ros.Buffer()
        self.listener = tf2_ros.TransformListener(self.buffer, self)
        self.create_subscription(PointStamped, '/camera_target_point', self.cb, 10)
        self.pub = self.create_publisher(PointStamped, '/base_target_point', 10)

    def cb(self, msg: PointStamped):
        try:
            transformed = tf2_geometry_msgs.do_transform_point(
                msg, self.buffer.lookup_transform('base_link', msg.header.frame_id, rclpy.time.Time()))
            self.pub.publish(transformed)
            self.get_logger().info(f"📍 转换后: {transformed.point}")
        except Exception as e:
            self.get_logger().error(f"TF转换失败: {e}")

def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(TFTransformer())
    rclpy.shutdown()
