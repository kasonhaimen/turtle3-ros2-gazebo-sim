import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    pkg_name = 'my_robot_description'
    pkg_share = get_package_share_directory(pkg_name)
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    # 1. 机器人状态发布器 (RSP) - 独立配置
    # slam-sim.launch.py 核心修改部分
    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            pkg_share, 'launch', 'real.launch.py'
            )]), 
        launch_arguments={
            'use_sim_time': use_sim_time,
            'frame_prefix': 'my_cool_robot/'  # <--- 这里精准对接 Gazebo 模型名称
            }.items()
    )
    # 2. Gazebo 仿真环境 (加载迷宫世界)
    world_file = os.path.join(pkg_share, 'worlds', 'maze_world.sdf')

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py'
            )]), 
            launch_arguments={
            'gz_args': f"-r {world_file}", # 替换为你实际的迷宫文件名
            'use_sim_time': use_sim_time
        }.items()
    )

    # 3. 独立桥接器：针对迷宫环境进行路径硬映射
    # 解决 "topic_name and ros_topic_name are mutually exclusive" 的唯一稳妥方案
    ros_gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        # 删掉 remappings 列表，全部写在 yaml 里
        parameters=[{
            'config_file': os.path.join(pkg_share, 'config', 'bridge_config_slam.yaml'),
            'use_sim_time': True
        }],
        output='screen'
    )

    # 4. 生成机器人实体 - 确保名字为 my_cool_robot
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            # 使用绝对路径 /robot_description，无视任何命名空间干扰
            '-topic', '/robot_description', 
            '-name', 'my_cool_robot',
            '-z', '0.1' 
        ],
        parameters=[{'use_sim_time': True}],
        output='screen'
    )

    # 5. SLAM Toolbox 节点
    slam_toolbox = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        parameters=[
            os.path.join(pkg_share, 'config', 'mapper_params_online_async.yaml'),
            {'use_sim_time': True}
        ],
        output='screen'
    )

    # 6. RViz2 节点
    rviz2 = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', os.path.join(pkg_share, 'rviz', 'slam.rviz')],
        parameters=[{'use_sim_time': True}]
    )

    # 7. 传感器坐标系软桥接 (2026 规范解法：不污染 URDF)
    # 作用：将 Gazebo 硬编码的传感器名字，对接回 URDF 标准名字
    node_stf_laser = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='laser_frame_bridge',
        arguments=[
            '0', '0', '0', '0', '0', '0',          # X Y Z Yaw Pitch Roll (完全重合)
            'my_cool_robot/laser_frame',           # 父级：URDF 生成在 TF 树上的标准名字
            'my_cool_robot/base_link/laser'        # 子级：Gazebo 强行发出的非标准名字
        ],
        parameters=[{'use_sim_time': True}],
        output='screen'
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        rsp,
        gazebo,
        ros_gz_bridge,
        spawn_entity,
        slam_toolbox,
        rviz2,
        node_stf_laser
    ])