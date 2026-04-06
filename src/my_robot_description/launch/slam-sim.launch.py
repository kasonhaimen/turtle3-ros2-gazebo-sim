import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, SetEnvironmentVariable, ExecuteProcess, LogInfo
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution

def generate_launch_description():
    # 1. 基础路径准备
    pkg_name = 'my_robot_description'
    pkg_share = get_package_share_directory(pkg_name)

    # 插件和模型路径（解决 Gazebo 找不到模型的问题）
    models_path = os.path.join(pkg_share, 'models')
    set_gz_resource_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=[models_path]
    )

    # 2. 声明启动参数
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    world_file = LaunchConfiguration('world', default='maze_world.sdf')

    # 3. 机器人状态发布器 (RSP) - 独立配置
    # slam-sim.launch.py 核心修改部分
    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            pkg_share, 'launch', 'real.launch.py'
            )]), 
        launch_arguments={
            'use_sim_time': use_sim_time,
            }.items()
    )
    # 4. Gazebo 仿真环境 (加载迷宫世界)包含 Gazebo 官方启动文件
    # 这会启动 gz-sim 并在后台运行服务器(server)和界面(gui)
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py'])
        ),
        launch_arguments={
            # -r 表示自动运行(run)，后面跟着世界文件的完整路径
            'gz_args':[PathJoinSubstitution([
                pkg_share, 'worlds', world_file]) , ' -r']
        }.items(),
    )

    # 5. 生成机器人实体 (spawn_entity)
    # 这不是启动 Gazebo 的一部分，但没有它 Gazebo 就是空的
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'my_cool_robot',
            '-topic', 'robot_description', # 对应 robot_state_publisher 发布的原始数据
            '-x', '0', '-y', '0', '-z', '0.1'
        ],
        output='screen',
    )

    # 6. 独立桥接器：针对迷宫环境进行路径硬映射
    # 解决 "topic_name and ros_topic_name are mutually exclusive" 的唯一稳妥方案
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        # 删掉 remappings 列表，全部写在 yaml 里
        parameters=[{
            'config_file': os.path.join(pkg_share, 'config', 'bridge_config_slam.yaml'),
            'use_sim_time': True
        }],
        output='screen'
    )



    # 7. SLAM Toolbox 节点 - 使用官方 launch 文件
    slam_toolbox = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            get_package_share_directory('slam_toolbox'), 'launch', 'online_async_launch.py'
        )]),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'slam_params_file': os.path.join(pkg_share, 'config', 'mapper_params_online_async.yaml')
        }.items()
    )

    # 8. RViz2 节点
    rviz2 = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', os.path.join(pkg_share, 'rviz', 'slam.rviz')],
        parameters=[{'use_sim_time': True}]
    )

    # 9. LaserScan frame_id 修复节点
    # Gazebo 生成的 frame_id 是 my_cool_robot/base_link/laser，但 URDF 中 link 是 laser_frame
    # 这个节点接收 /scan 并重新发布为 frame_id=laser_frame
    scan_fixer_script = os.path.join(pkg_share, 'scripts', 'scan_frame_fixer.py')
    scan_fixer = ExecuteProcess(
        cmd=['/usr/bin/python3', scan_fixer_script],
        output='screen'
    )

    # --- 最终返回部分 ---
    return LaunchDescription([
        # 环境变量
        set_gz_resource_path,
        
        # 参数声明
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('world', default_value='maze_world.sdf'),

        # 节点与功能
        rsp,
        gz_sim,
        spawn_robot,
        bridge,
        slam_toolbox,
        rviz2,
        scan_fixer
    ])