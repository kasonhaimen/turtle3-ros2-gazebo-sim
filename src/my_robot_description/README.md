# 项目简介
这是一个仿照turtle3小车打造的机器人工程，源码目录如下
kason@kason-windows:~/ros2_ws/src/my_robot_description$ tree
.
├── CMakeLists.txt
├── config
│   └── bridge_config.yaml
├── include
│   └── my_robot_description
├── launch
│   ├── rsp.launch.py #真实世界启动脚本
│   ├──sim.launch.py #gazebo启动脚本
|   └──slam-sim.launch.py #gazebo启动脚本slam版
├── meshes
├── models
├── package.xml
├── scripts
│   ├── obstacle_avoidance.py #小车简易避障脚本
    ├── slam_explore.py # 小车slam脚本
│   └── star_planner_pid.py #小车画五角星脚本
├── src
├── urdf
│   └── robot.urdf.xacro #避障小车
└── worlds # 机器人工作的世界
    └── maze_world.sdf


config/bridge_config.yaml文件定义了topic和type，含盖下列内容：
激光雷达扫描"/scan"
运动控制指令"/cmd_vel"
关节状态"/joint_states"
里程计数据"/odom"