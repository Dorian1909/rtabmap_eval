"""Evaluation-side launch: auxiliary nodes + TF recorder + bag playback.

Launched once per run by runner.run_single_bag(). The user-provided
RTAB-Map launch (configured via `paths.launch_cmd`) is started separately
and is NOT included here.

Robot-specific configuration (static TF values, which aux nodes to enable,
bag playback delay) is passed as launch arguments from the `eval_launch`
section of the YAML config — see runner.py's `eval_launch_args`.

Lifecycle:
  - All enabled auxiliary nodes start immediately.
  - `ros2 bag play` starts after `bag_start_delay_s` seconds to ensure
    auxiliary nodes are ready.
  - When bag play exits, `OnProcessExit` triggers `ShutdownAction` and the
    launch framework cleans up all auxiliary processes.

Required launch arguments (set by runner.py):
  bag_path     Path to the bag directory to play.
  traj_file    Output path for the recorded TUM trajectory.
  record_rate  TF recording rate (Hz).

Optional launch arguments (set from eval_launch config section):
  static_tf_x/y/z/roll/pitch/yaw/parent/child  Static TF values.
  enable_static_tf / enable_nv12_to_bgr / enable_odom_to_tf
  enable_foxglove / enable_rviz / enable_rtabmap_viz  Toggles.
  bag_start_delay_s  Delay before starting bag playback.
"""

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    RegisterEventHandler,
    Shutdown,
    TimerAction,
)
from launch.event_handlers import OnProcessExit
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, SetUseSimTime


def generate_launch_description():
    # Bag playback process, started after `bag_start_delay_s` via TimerAction.
    # OnProcessExit below watches this exact action; when bag play exits
    # (playback finished), ShutdownAction tears down the whole launch and
    # the launch framework cleans up all auxiliary processes.
    bag_player = ExecuteProcess(
        cmd=['ros2', 'bag', 'play', LaunchConfiguration('bag_path'), '--clock'],
        output='screen',
        name='bag_player')

    return LaunchDescription([
        SetUseSimTime(True),

        # Required arguments (filled by runner.py)
        DeclareLaunchArgument('bag_path', description='Path to the bag directory to play.'),
        DeclareLaunchArgument('traj_file', description='Output path for the recorded TUM trajectory.'),
        DeclareLaunchArgument('record_rate', default_value='20.0',
                              description='TF recording rate (Hz).'),

        # Robot-specific arguments (filled from eval_launch config section)
        DeclareLaunchArgument('static_tf_x', default_value='0.0'),
        DeclareLaunchArgument('static_tf_y', default_value='0.0'),
        DeclareLaunchArgument('static_tf_z', default_value='0.0'),
        DeclareLaunchArgument('static_tf_roll', default_value='-1.5708'),
        DeclareLaunchArgument('static_tf_pitch', default_value='0.0'),
        DeclareLaunchArgument('static_tf_yaw', default_value='-1.544'),
        DeclareLaunchArgument('static_tf_parent', default_value='base_footprint'),
        DeclareLaunchArgument('static_tf_child', default_value='camera_depth_frame'),
        DeclareLaunchArgument('enable_static_tf', default_value='true'),
        DeclareLaunchArgument('enable_nv12_to_bgr', default_value='true'),
        DeclareLaunchArgument('enable_odom_to_tf', default_value='true'),
        DeclareLaunchArgument('enable_foxglove', default_value='true'),
        DeclareLaunchArgument('enable_rviz', default_value='false'),
        DeclareLaunchArgument('enable_rtabmap_viz', default_value='false'),
        DeclareLaunchArgument('bag_start_delay_s', default_value='3.0',
                              description='Delay before starting bag playback (s).'),

        # NV12 -> BGR8 converter (optional)
        Node(
            package='rtabmap_eval', executable='nv12_to_bgr',
            name='nv12_to_bgr', output='screen',
            condition=IfCondition(LaunchConfiguration('enable_nv12_to_bgr'))),

        # Publish odom -> base_footprint TF from /odom topic (optional)
        Node(
            package='rtabmap_eval', executable='odom_to_tf',
            name='odom_to_tf', output='screen',
            condition=IfCondition(LaunchConfiguration('enable_odom_to_tf'))),

        # Static TF: parent → child (optional, configurable via static_tf_* args).
        # Humble's static_transform_publisher uses named flags (--x, --y, ...)
        # rather than positional args — positional args are silently ignored.
        Node(
            package='tf2_ros', executable='static_transform_publisher',
            arguments=[
                '--x', LaunchConfiguration('static_tf_x'),
                '--y', LaunchConfiguration('static_tf_y'),
                '--z', LaunchConfiguration('static_tf_z'),
                '--roll', LaunchConfiguration('static_tf_roll'),
                '--pitch', LaunchConfiguration('static_tf_pitch'),
                '--yaw', LaunchConfiguration('static_tf_yaw'),
                '--frame-id', LaunchConfiguration('static_tf_parent'),
                '--child-frame-id', LaunchConfiguration('static_tf_child'),
            ],
            condition=IfCondition(LaunchConfiguration('enable_static_tf'))),

        Node(
            package='tf2_ros', executable='static_transform_publisher',
            arguments=[
                '--x', '0.0',
                '--y', '0.0',
                '--z', '0.0',
                '--roll', '0.0',
                '--pitch', '0.0',
                '--yaw', '0.0',
                '--frame-id', 'base_footprint',
                '--child-frame-id', 'base_link',
            ],
            condition=IfCondition(LaunchConfiguration('enable_static_tf'))),

        # TF recorder (map -> base_footprint) -> TUM trajectory.
        # Registered as a console_scripts entry point in setup.py; output_path
        # and rate_hz are passed as ROS parameters.
        Node(
            package='rtabmap_eval', executable='record_tf_trajectory',
            name='tf_recorder',
            parameters=[{
                'output_path': LaunchConfiguration('traj_file'),
                'rate_hz': LaunchConfiguration('record_rate'),
            }]),

        # Foxglove WebSocket bridge (optional)
        Node(
            package='foxglove_bridge', executable='foxglove_bridge', output='screen',
            condition=IfCondition(LaunchConfiguration('enable_foxglove')),
            parameters=[{'port': 8765}]),

        # RTAB-Map GUI (optional)
        Node(
            package='rtabmap_viz', executable='rtabmap_viz', output='screen',
            condition=IfCondition(LaunchConfiguration('enable_rtabmap_viz'))),

        # RViz (optional)
        Node(
            package='rviz2', executable='rviz2', name='rviz2', output='screen',
            condition=IfCondition(LaunchConfiguration('enable_rviz'))),

        # Bag playback: delayed so auxiliary nodes are ready first.
        TimerAction(
            period=LaunchConfiguration('bag_start_delay_s'),
            actions=[bag_player]),

        # When bag play exits, tear down the whole launch — all aux processes
        # are cleaned up by the launch framework.
        RegisterEventHandler(
            OnProcessExit(
                target_action=bag_player,
                on_exit=[Shutdown(reason='bag playback finished')])),
    ])
