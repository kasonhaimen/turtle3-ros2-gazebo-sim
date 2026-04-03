import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import xacro

def generate_launch_description():
# 1. 声明路径和包名
    pkg_path = get_package_share_directory('my_robot_description')

# 1. 新增：声明 frame_prefix 参数，默认值为空字符串（适配真实机器人）
    declare_frame_prefix = DeclareLaunchArgument(
        'frame_prefix',
        default_value='',
        description='Prefix for robot frames (e.g. my_cool_robot/)'
    )
    frame_prefix = LaunchConfiguration('frame_prefix')

    # 2. 【核心】定义 Launch 参数 (DeclareLaunchArgument)
    # 这些参数可以从命令行传入，例如：ros2 launch ... use_sim_time:=true
    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation (Gazebo) clock if true'
    )
    
    # 3. 【核心】获取参数的值 (LaunchConfiguration)
    # 这里的 use_sim_time 不是 Python 字符串，而是一个在运行时才会被替换的变量
    use_sim_time = LaunchConfiguration('use_sim_time')

    # 4. 解析 Xacro 文件
    xacro_file = os.path.join(pkg_path, 'urdf', 'robot.urdf.xacro')
    robot_description_config = xacro.process_file(xacro_file).toxml()  
    
    # 5. 配置节点
    # 2. 修改：将参数传给 RSP
    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description_config,
            'use_sim_time': use_sim_time,
            'frame_prefix': frame_prefix  # <--- 关键注入
        }]
    )

    # 添加这个节点：关节状态发布器（带界面）
    node_joint_state_publisher_gui = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        output='screen'
    )

    # 6. 返回包含所有声明和节点的列表
    return LaunchDescription([
        declare_use_sim_time,          # 必须先声明参数
        node_robot_state_publisher,     # 再运行依赖参数的节点
        #node_joint_state_publisher_gui  # <--- 新增
    ])