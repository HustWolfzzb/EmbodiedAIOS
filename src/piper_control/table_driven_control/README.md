# 表驱动的六自由度机械臂末端位姿控制

详见[表驱动的机械臂末端位姿控制](https://s1vvxephwhf.feishu.cn/wiki/IAjFw7g63i2J7ikx9AvcGqjonls)

## 用法

### 生成位姿与关节角度的对应表

```bash
python generate_table.py
```

1. 需要两个mujoco描述文件，分别描述拟人臂和球形腕臂部分，详见代码中的路径
2. 生成两个`.kdtree`文件

### 控制机械臂的demo
    
```bash
python table_driven_ctrl.py
```

### 指定末端位姿获取关节角度

```python
from table_driven_ctrl import TableDrivenControl

table_control = TableDrivenControl()
joints = table_control.get_control_action(
    ee_pos=[0.5, 0.0, 0.1],
    ee_euler=[0.0, 3 * np.pi / 4, 0.0],
)
```
