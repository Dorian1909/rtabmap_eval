"""
RTAB-Map launch for bag playback with Foxglove visualization

Usage:
  Terminal 1 - Launch RTAB-Map:
    $ source /opt/ros/humble/setup.bash
    $ source ~/catkin_ws/install/setup.bash
    $ ros2 launch /home/dpx/rtabmap_bag_demo.launch.py

  Terminal 2 - Play bag:
    $ source /opt/ros/humble/setup.bash
    $ ros2 bag play /home/dpx/rosbag2_2026_02_12-16_42_58 --clock

  Browser - Open Foxglove:
    https://app.foxglove.dev/~/view?ds=ros2-websocket
    (connects to ws://localhost:8765)
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition
from launch_ros.actions import Node
from launch_ros.actions import SetParameter

# XFeat environment
import os
os.environ["RTABMAP_XFEAT_REPO"] = "/home/dpx/xfeat_compare/accelerated_features"
os.environ["RTABMAP_XFEAT_WEIGHTS"] = "/home/dpx/xfeat_compare/accelerated_features/weights/xfeat.pt"

def generate_launch_description():

    parameters = {
        'Rtabmap/DetectionRate': '5',
        'frame_id': 'base_footprint',
        'odom_frame_id': 'odom',
        'subscribe_rgbd': False,
        'subscribe_depth': True,
        'approx_sync': True,
        'sync_queue_size': 10,
        'RGBD/NeighborLinkRefining': 'false',
        'RGBD/ProximityBySpace': 'true',
        'RGBD/ProximityByTime': 'false',
        'RGBD/ProximityOdomGuess': 'true',
        'Reg/Strategy': '0',
        'Vis/MinInliers': '10',
        'RGBD/OptimizeMaxError': '2.0',
        'Optimizer/Robust': 'true',
        'RGBD/OptimizeFromGraphEnd': 'false',
        'RGBD/AngularUpdate': '0.01',
        'RGBD/LinearUpdate': '0.01',
        'Mem/STMSize': '10',
        'Grid/RangeMin': '0.1',
        'Grid/RangeMax': '50.0',
        'Vis/FeatureType': '15',
        'PyDetector/Path': '/home/dpx/catkin_ws/src/rtabmap/corelib/src/python/rtabmap_xfeat.py',
        'PyDetector/Cuda': 'false',
        'Vis/MaxFeatures': '2048',
        'Vis/CorNNType': '9',
        'RGBD/LoopClosureReextractFeatures': 'true',
        'Vis/PnPVarianceMedianRatio': '100',
        'Vis/PnPFlags': '1',
        'Vis/PnPReprojError': '2.0',
        'Vis/PnPRefineIterations': '5',
        'Vis/MinInliers': '10',
            }

    remappings = [
        ('rgb/image', '/StereoNetNode/rectified_image_bgr'),
        ('depth/image', '/StereoNetNode/stereonet_depth'),
        ('rgb/camera_info', '/StereoNetNode/rectify_left_image/camera_info'),
        ('odom', '/odom'),
    ]

    return LaunchDescription([
        SetParameter(name='use_sim_time', value=True),

        DeclareLaunchArgument('localization', default_value='false',
                              description='Launch in localization mode.'),
        DeclareLaunchArgument('foxglove', default_value='true',
                              description='Launch Foxglove bridge (web-based visualization).'),
        DeclareLaunchArgument('rviz', default_value='false',
                              description='Launch RVIZ (requires OpenGL 1.5+, broken on some WSL2 setups).'),
        DeclareLaunchArgument('rtabmap_viz', default_value='false',
                              description='Launch RTAB-Map GUI (requires OpenGL).'),

        # NV12 -> BGR8 converter
        ExecuteProcess(
            cmd=['python3', '/home/dpx/nv12_to_bgr.py'],
            output='screen'),

        # Publish odom -> base_footprint TF from /odom topic
        ExecuteProcess(
            cmd=['python3', '/home/dpx/odom_to_tf.py'],
            output='screen'),

        # Static TF: base_footprint -> camera_depth_frame
        # Rotation: camera_depth_frame is optical (X-right, Y-down, Z-forward)
        # base_footprint is robot frame (X-forward, Y-left, Z-up)
        # yaw=-90?? then roll=-90?? converts robot frame -> optical frame
        Node(
            package='tf2_ros', executable='static_transform_publisher',
            arguments=['0', '0', '0', '-1.5708', '0', '-1.544', 'base_footprint', 'camera_depth_frame']),

        # SLAM - subscribe to individual topics directly (no rgbd_sync)
        Node(
            package='rtabmap_slam', executable='rtabmap', output='screen',
            parameters=[parameters, {'qos': 2, 'qos_image': 2}],
            remappings=remappings,
            arguments=['-d']),

        # Foxglove WebSocket bridge
        Node(
            package='foxglove_bridge', executable='foxglove_bridge', output='screen',
            condition=IfCondition(LaunchConfiguration('foxglove')),
            parameters=[{'port': 8765}]),

        # Visualization: RTAB-Map GUI
        Node(
            package='rtabmap_viz', executable='rtabmap_viz', output='screen',
            condition=IfCondition(LaunchConfiguration('rtabmap_viz')),
            parameters=[parameters],
            remappings=remappings),

        # Visualization: RViz
        Node(
            package='rviz2', executable='rviz2', name='rviz2', output='screen',
            condition=IfCondition(LaunchConfiguration('rviz')),
            arguments=['-d', '/home/dpx/rtabmap_bag_demo.rviz']),
    ])