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

    # 定义 use_sim_time 变量，方便统一管理
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    # 1. 模型发布节点 (RSP)
    # 确保它发布的 TF 数据带有仿真时间戳
    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            pkg_share, 'launch', 'rsp.launch.py'
        )]), launch_arguments={'use_sim_time': use_sim_time}.items()
    )

    # 2. 启动 Gazebo Harmonic
    # 添加 use_sim_time 确保仿真引擎同步
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py'
        )]), launch_arguments={
            'gz_args': '-r empty.sdf',
            'use_sim_time': use_sim_time
        }.items()
    )

    # 3. 桥接器配置 (Bridge)
    bridge_config = os.path.join(pkg_share, 'config', 'bridge_config_sim.yaml')

    ros_gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{
            'config_file': bridge_config,
            'use_sim_time': True # 解决 TF_OLD_DATA 的关键：让桥接器意识到自己在仿真环境
        }],
        output='screen'
    )

    # 4. 在 Gazebo 中生成机器人
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-topic', 'robot_description',
            '-name', 'my_cool_robot',
            '-z', '0.1' ,
            '-x', '-1',
        ],
        parameters=[{'use_sim_time': True}], # 同样建议加上
        output='screen'
    )

    # 5激光雷达过滤器节点
    # 1. 获取配置文件的绝对路径
    package_name = 'my_robot_description' # 替换为你的功能包名
    filter_config = os.path.join(
        get_package_share_directory(package_name),
        'config',
        'my_laser_filter.yaml'
    )

    return LaunchDescription([
        # 声明参数，这样你可以在命令行通过 use_sim_time:=false 覆盖它（虽然一般不这么干）
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        rsp,
        gazebo,
        ros_gz_bridge,
        spawn_entity
    ])