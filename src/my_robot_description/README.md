# my_robot_description

ROS2 Jazzy + Gazebo Harmonic 机器人仿真工程，仿照 TurtleBot3 构建的小车机器人，支持 SLAM 建图与导航。

## 环境要求

- ROS 2 Jazzy
- Gazebo Harmonic
- slam_toolbox

## 项目结构

```
my_robot_description/
├── config/                      # 配置文件
│   ├── bridge_config_sim.yaml   # Gazebo仿真桥接配置
│   ├── bridge_config_slam.yaml  # SLAM仿真桥接配置
│   └── mapper_params_online_async.yaml  # SLAM参数配置
├── docs/                        # 问题排查文档
│   ├── problem1_laserScan_no_display.md  # LaserScan不显示问题分析
│   └── problem2_no_map_frame.md          # 无map frame问题分析
├── launch/                      # 启动文件
│   ├── real.launch.py          # 真实机器人启动脚本
│   ├── sim.launch.py            # Gazebo仿真启动脚本
│   └── slam-sim.launch.py       # SLAM仿真启动脚本
├── models/                      # Gazebo模型
├── rviz/                        # RViz配置
│   └── slam.rviz               # SLAM仿真RViz配置
├── scripts/                     # Python脚本
│   ├── check_scan.py           # LaserScan诊断脚本
│   ├── check_scan_fixed.py     # /scan_fixed诊断脚本
│   ├── scan_frame_fixer.py     # LaserScan frame_id修复节点
│   ├── obstacle_avoidance.py    # 简易避障脚本
│   ├── slam_explore.py         # SLAM探索脚本
│   └── star_planner_pid.py     # 五角星轨迹脚本
├── urdf/                       # URDF文件
│   └── robot.urdf.xacro       # 机器人描述文件
├── worlds/                      # Gazebo世界文件
│   ├── maze_world.sdf          # 迷宫世界
│   └── living_room.sdf        # 客厅世界
├── CMakeLists.txt
└── package.xml
```

## 快速开始

### 编译

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select my_robot_description
source install/setup.bash
```

### 启动仿真

**SLAM仿真（推荐）：**
```bash
ros2 launch my_robot_description slam-sim.launch.py
```

**基础仿真：**
```bash
ros2 launch my_robot_description sim.launch.py
```

**真实机器人：**
```bash
ros2 launch my_robot_description real.launch.py
```

### 运行功能脚本

**避障：**
```bash
ros2 run my_robot_description obstacle_avoidance.py
```

**五角星轨迹：**
```bash
ros2 run my_robot_description star_planner_pid.py
```

**SLAM探索：**
```bash
ros2 run my_robot_description slam_explore.py
```

## TF Tree

仿真启动后的完整TF树：
```
                    map
                      │
                      └── odom
                           │
                           └── base_link
                                ├── left_wheel
                                ├── right_wheel
                                └── chassis
                                      ├── caster_wheel
                                      └── laser_frame
```

## 话题说明

| 话题 | 类型 | 说明 |
|------|------|------|
| `/scan` | sensor_msgs/LaserScan | 原始激光扫描（Gazebo发布） |
| `/scan_fixed` | sensor_msgs/LaserScan | 修复frame_id后的激光扫描 |
| `/cmd_vel` | geometry_msgs/Twist | 运动控制指令 |
| `/joint_states` | sensor_msgs/JointState | 关节状态 |
| `/odom` | nav_msgs/Odometry | 里程计数据 |
| `/tf` | tf2_msgs/TFMessage | 坐标变换 |

## 已知问题与解决

### 问题1：LaserScan不显示红点

**现象**：RViz中LaserScan面板没有显示激光扫描点

**原因**：Gazebo Harmonic生成的LaserScan消息中`header.frame_id`是`my_cool_robot/base_link/laser`，与URDF中定义的`laser_frame`不匹配

**解决**：使用`scan_frame_fixer.py`节点将`/scan`重新发布为`/scan_fixed`，修复frame_id

详见 [docs/problem1_laserScan_no_display.md](docs/problem1_laserScan_no_display.md)

### 问题2：没有map frame

**现象**：TF tree中只有`odom → base_link`，没有`map → odom`

**原因**：slam_toolbox是LifecycleNode，需要正确配置和激活才能正常工作

**解决**：使用slam_toolbox官方的`online_async_launch.py`启动文件

详见 [docs/problem2_no_map_frame.md](docs/problem2_no_map_frame.md)

## 机器人模型

仿 TurtleBot3 的差速驱动小车：
- 2个主动轮（left_wheel, right_wheel）
- 1个万向轮（caster_wheel）
- 1个激光雷达（laser_frame）
- GPU加速激光传感器（Gazebo Harmonic）

## 参考项目

本项目参考了 [Road-Balance/ignition_tutorial](https://github.com/Road-Balance/ignition_tutorial)，学习其架构思想并适配到 ROS 2 Jazzy + Gazebo Harmonic。

## License

TODO
