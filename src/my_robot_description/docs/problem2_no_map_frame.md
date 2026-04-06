# 问题2：没有 map frame

## 问题描述

TF tree中只有 `odom → base_link`，没有 `map → odom` 的变换，slam_toolbox没有创建map frame。

## 排查过程

### 1. 检查TF tree

```bash
ros2 run tf2_tools view_frames
```

**检查结果**：
```
base_link: 
  parent: 'odom'
left_wheel: 
  parent: 'base_link'
right_wheel: 
  parent: 'base_link'
caster_wheel: 
  parent: 'chassis'
chassis: 
  parent: 'base_link'
laser_frame: 
  parent: 'chassis'
```

确认缺少 `map` frame。

### 2. 检查slam_toolbox进程

```bash
ps aux | grep slam_toolbox | grep -v grep
```

**检查结果**：
```
kason  27079  6.8  0.4  763768 35828 pts/7  Sl+  02:18  0:04 /opt/ros/jazzy/lib/slam_toolbox/async_slam_toolbox_node --ros-args -r __node:=slam_toolbox --params-file /home/kason/ros2_ws/install/my_robot_description/share/my_robot_description/config/mapper_params_online_async.yaml
```

slam_toolbox进程在运行。

### 3. 检查slam_toolbox日志

```bash
cat ~/.ros/log/async_slam_toolbox_node_*.log
```

**检查结果**：
```
[INFO] [1775499023.338891629] [slam_toolbox]: Node using stack size 40000000
```

日志异常稀少，只有初始化信息，说明slam_toolbox可能没有正常工作。

### 4. 检查topic订阅

```bash
python3 -c "
import rclpy
rclpy.init()
node = rclpy.create_node('test')
topics = node.get_topic_names_and_types()
for t, types in topics:
    if 'map' in t.lower() or 'slam' in t.lower():
        print(f'{t}: {types}')
rclpy.shutdown()
"
```

**检查结果**：
```
/slam_toolbox/transition_event: ['lifecycle_msgs/msg/TransitionEvent']
```

没有map相关topic，slam_toolbox没有发布任何地图数据。

### 5. 检查参数加载

```bash
cat /tmp/launch_params_*.log 2>/dev/null | head -20
# 或
cat /proc/$(pgrep -f async_slam_toolbox | head -1)/cmdline | tr '\0' ' '
```

**检查结果**：发现slam_toolbox的参数文件被传递了两次：
```
--params-file /home/kason/ros2_ws/install/my_robot_description/share/my_robot_description/config/mapper_params_online_async.yaml
--params-file /tmp/launch_params_xxx
```

第二个临时文件只有 `use_sim_time: true`，覆盖了完整的yaml配置。

### 6. 检查yaml配置

```bash
grep scan_topic /home/kason/ros2_ws/install/my_robot_description/share/my_robot_description/config/mapper_params_online_async.yaml
```

**检查结果**：
```
scan_topic: /scan_fixed
```

配置是正确的，使用了 `/scan_fixed`。

## 问题原理

### 官方launch文件分析

查看官方launch文件 `/opt/ros/jazzy/share/slam_toolbox/launch/online_async_launch.py`：

```python
start_async_slam_toolbox_node = LifecycleNode(
    parameters=[
      slam_params_file,
      {
        'use_lifecycle_manager': use_lifecycle_manager,
        'use_sim_time': use_sim_time
      }
    ],
    package='slam_toolbox',
    executable='async_slam_toolbox_node',
    name='slam_toolbox',
    output='screen',
    namespace=''
)
```

**关键发现：官方使用 `LifecycleNode`，而不是普通的 `Node`。**

### LifecycleNode 的生命周期

ROS2 的 LifecycleNode 有多个状态：

- **Unconfigured**（未配置）- 节点刚启动时的状态
- **Inactive**（不活跃）- 已配置但未激活
- **Active**（活跃）- 正在工作

slam_toolbox 是一个 LifecycleNode，需要被正确地配置和激活才能正常工作。

### 官方launch还做了这些（第55-77行）：

```python
# 配置 slam_toolbox
configure_event = EmitEvent(
    event=ChangeState(
      lifecycle_node_matcher=matches_action(start_async_slam_toolbox_node),
      transition_id=Transition.TRANSITION_CONFIGURE
    ),
    ...
)

# 激活 slam_toolbox
activate_event = RegisterEventHandler(
    OnStateTransition(
        target_lifecycle_node=start_async_slam_toolbox_node,
        ...
        EmitEvent(event=ChangeState(
            lifecycle_node_matcher=matches_action(start_async_slam_toolbox_node),
            transition_id=Transition.TRANSITION_ACTIVATE
        ))
    ),
    ...
)
```

### 为什么直接用 Node 会失败

当我们直接用 `Node` 启动 slam_toolbox 时：

1. 节点启动但处于 **Unconfigured** 状态
2. 没有任何配置/激活的事件被触发
3. slam_toolbox 虽然进程在运行，但没有正常工作（不发布 map）

### 参数覆盖问题（次要原因）

之前使用的启动方式：
```python
slam_toolbox = Node(
    package='slam_toolbox',
    executable='async_slam_toolbox_node',
    parameters=[
        yaml_file,
        {'use_sim_time': True}  # 这个会覆盖yaml中的参数
    ]
)
```

这种方式导致yaml中的所有参数被 `{'use_sim_time': True}` 覆盖，只保留了 `use_sim_time`，其他参数（包括 `scan_topic: /scan_fixed`）丢失。

### 总结

**直接用 Node 失败的主要原因是：没有正确管理 LifecycleNode 的生命周期。**

slam_toolbox 需要被显式地配置（CONFIGURE）和激活（ACTIVATE）才能正常工作。官方 launch 文件使用 `LifecycleNode` + 事件处理器来自动完成这个过程，而直接用 `Node` 则跳过了这个关键步骤。

## 解决方法

### 步骤1：修改launch文件

修改 `launch/slam-sim.launch.py`，使用官方launch文件：

```python
# 原来直接启动Node的方式（有问题）
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

# 改为使用官方launch文件
slam_toolbox = IncludeLaunchDescription(
    PythonLaunchDescriptionSource([os.path.join(
        get_package_share_directory('slam_toolbox'), 
        'launch', 'online_async_launch.py'
    )]),
    launch_arguments={
        'use_sim_time': use_sim_time,
        'slam_params_file': os.path.join(pkg_share, 'config', 'mapper_params_online_async.yaml')
    }.items()
)
```

### 步骤2：在yaml中添加use_sim_time

修改 `config/mapper_params_online_async.yaml`：

```yaml
slam_toolbox:
  ros__parameters:
    # ROS Parameters
    odom_frame: odom
    map_frame: map
    base_frame: base_link
    scan_topic: /scan_fixed
    use_map_saver: true
    mode: mapping
    use_sim_time: true    # 添加这一行
    # ... 其他参数
```

## 验证结果

修复后运行：

```bash
ros2 run tf2_tools view_frames
```

**输出结果**：
```
map: 
  parent: 'odom'
odom: 
  parent: 'map'
base_link: 
  parent: 'odom'
left_wheel: 
  parent: 'base_link'
right_wheel: 
  parent: 'base_link'
caster_wheel: 
  parent: 'chassis'
chassis: 
  parent: 'base_link'
laser_frame: 
  parent: 'chassis'
```

TF tree现在完整了：
```
map → odom → base_link → left_wheel
                       → right_wheel
                       → chassis → caster_wheel
                                 → laser_frame
```

slam_toolbox现在正常工作了，创建了 `map → odom` 的变换。

## 最终TF Tree

修复后的完整TF树：
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
