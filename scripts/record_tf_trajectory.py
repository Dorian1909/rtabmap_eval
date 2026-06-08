#!/usr/bin/env python3
"""
Record TF map->base_footprint as TUM trajectory while RTAB-Map is running.

Usage:
    python3 /home/dpx/record_tf_trajectory.py [output_path] [rate_hz]

Output: TUM format file (timestamp x y z qx qy qz qw)
"""

import sys
import os
import signal
import rclpy
from rclpy.node import Node
from tf2_ros import Buffer, TransformListener
from collections import deque


class TfRecorder(Node):
    def __init__(self, output_path, rate_hz=20.0):
        super().__init__('tf_recorder')
        self.output_path = output_path
        self.poses = deque()
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.create_timer(1.0 / rate_hz, self.record_pose)
        self.get_logger().info(
            f'Recording map->base_footprint at {rate_hz}Hz -> {output_path}')

    def record_pose(self):
        try:
            t = self.tf_buffer.lookup_transform(
                'map', 'base_footprint', rclpy.time.Time())
            ts = t.header.stamp.sec + t.header.stamp.nanosec * 1e-9
            p = t.transform.translation
            r = t.transform.rotation
            self.poses.append(
                f'{ts:.9f} {p.x:.6f} {p.y:.6f} {p.z:.6f} '
                f'{r.x:.6f} {r.y:.6f} {r.z:.6f} {r.w:.6f}')
        except Exception:
            pass

    def save(self):
        with open(self.output_path, 'w') as f:
            f.write('\n'.join(self.poses))
            if self.poses:
                f.write('\n')
        self.get_logger().info(f'Saved {len(self.poses)} poses to {self.output_path}')


def main():
    output_path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/tf_trajectory.tum'
    rate_hz = float(sys.argv[2]) if len(sys.argv) > 2 else 20.0

    rclpy.init()
    node = TfRecorder(output_path, rate_hz)

    def shutdown(sig, frame):
        node.save()
        node.destroy_node()
        rclpy.shutdown()
        os._exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.save()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
