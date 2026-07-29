"""Convert nv12 image to bgr8 for RTAB-Map compatibility."""

import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class Nv12ToBgr(Node):
    def __init__(self):
        super().__init__('nv12_to_bgr',
            automatically_declare_parameters_from_overrides=True)
        self.bridge = CvBridge()
        self.pub = self.create_publisher(Image, '/image_left_raw_rgb', 10)
        self.sub = self.create_subscription(
            Image, '/StereoNetNode/rectify_left_image',
            self.callback, 10)

    def callback(self, msg):
        if msg.encoding != 'nv12':
            self.pub.publish(msg)
            return
        # NV12: Y plane (height*1.5 x width) -> BGR
        data = np.frombuffer(msg.data, dtype=np.uint8)
        height = msg.height
        width = msg.width
        y_plane = data[:height * width].reshape((height, width))
        uv_plane = data[height * width:].reshape((height // 2, width))
        # Interleave U and V
        u = uv_plane[:, 0::2]
        v = uv_plane[:, 1::2]
        # Upsample UV to full resolution
        u_full = np.repeat(np.repeat(u, 2, axis=0), 2, axis=1)
        v_full = np.repeat(np.repeat(v, 2, axis=0), 2, axis=1)
        # YUV to BGR conversion (BT.601)
        y = y_plane.astype(np.float32)
        u = u_full.astype(np.float32) - 128.0
        v = v_full.astype(np.float32) - 128.0
        b = np.clip(y + 1.772 * u, 0, 255).astype(np.uint8)
        g = np.clip(y - 0.344 * u - 0.714 * v, 0, 255).astype(np.uint8)
        r = np.clip(y + 1.402 * v, 0, 255).astype(np.uint8)
        bgr = np.stack([b, g, r], axis=2)
        out_msg = self.bridge.cv2_to_imgmsg(bgr, encoding='bgr8')
        out_msg.header = msg.header
        self.pub.publish(out_msg)


def main():
    rclpy.init()
    node = Nv12ToBgr()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
