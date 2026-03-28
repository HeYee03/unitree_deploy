# Unitree G1 Virtual Controller / 虚拟手柄使用说明

本项目包含一个基于 Pygame 的虚拟手柄控制界面，在没有物理手柄时，能够让你直接使用鼠标和键盘来控制 `unitree_mujoco` 仿真环境中的 G1 机器人。

## 1. 运行依赖

如果要使用此虚拟手柄界面，你需要确保安装了 `pygame`。在配置好的 Python 环境（如 `isaaclab50`）下运行：

```bash
pip install pygame
```

## 2. 启动流程说明

你需要同时启动**两个终端**。

### 终端 1：启动 Python 仿真器和控制界面 (GUI)

首先启动 MuJoCo 仿真器进程：

```bash
cd ~/unitree_rl_lab-main/unitree_deploy/unitree_mujoco/simulate_python
python unitree_mujoco.py
```
> **注意**：启动后，你将会看到两个窗口弹出来，一个是 **MuJoCo 的 3D 渲染窗口**，另一个是名字叫 **"Virtual Controller" 的黑色控制界面**。

### 终端 2：启动机器人底层控制逻辑 (g1_ctrl)

保持 Python 仿真器在运行，打开一个新的终端标签页：

```bash
cd ~/unitree_rl_lab-main/unitree_deploy/deploy/robots/g1_29dof/build
# 必须带上 `-n lo` 让它连接本地的 DDS 通信
./g1_ctrl -n lo
```

## 3. 机器人初始化与起立流程

启动两个终端后，机器人初始被挂在空中的绳子上。你需要按照以下顺序操作将它激活并放到地上：

1. **状态一 (FixStand)：点击 ▲ Stand**
   - 单击 **"Virtual Controller"** 控制面板上的蓝色 **【▲ Stand】** 按钮。（该按钮等效于物理手柄的 `L2 + Up`）。
   - **观察**：终端 2 (`g1_ctrl`) 应该会打印出状态变化：`FSM: Passive -> FixStand`。
2. **下降到地面：按下 8**
   - 切换到 **MuJoCo 3D 渲染窗口**。
   - 在键盘上按下数字键 **`8`**，让机器人从空中被下降到在地上站立的姿态。
3. **状态二 (Velocity 行走模式)：点击 ▶ Walk**
   - 切换回 **"Virtual Controller"** 窗口，点击绿色的 **【▶ Walk】** 按钮。（等效于物理手柄的 `R1 + X`）。
   - **观察**：终端 2 应该会打印出状态变化：`FSM: FixStand -> Velocity`。此时机器人进入了可以行走的控制模式。
4. **松开绳子：按下 9**
   - 切回 **MuJoCo** 窗口。
   - 在键盘上按下数字键 **`9`**，松开机器人背后的挂绳。现在你可以自由操控他了！

## 4. 控制操作说明

一旦机器人进入了 Velocity 行走模式并且松开了绳子，你可以通过以下方式全方向控制你的机器人：

### 方式 一：使用鼠标拖拽 (GUI 摇杆)

在 **"Virtual Controller"** 窗口中，你可以直接拖动面板上的圆形虚拟摇杆：
- **左侧摇杆 (Move)**：控制机器人的**前后移动** (Forward/Backward) 与 **左右平移** (Strafe Left/Right)。
- **右侧摇杆 (Turn)**：控制机器人的**左右转向** (Turn Left/Right)。

### 方式 二：使用键盘 (WSAD)
> ⚠️ **关键说明**：若要使用键盘快捷键，你必须先点击一下 "Virtual Controller" 的窗口，**确保输入焦点在虚拟手柄面板上（而不是在 MuJoCo 窗口里）**。

- **平移控制**：
  - `W` / `S`：前进 / 后退
  - `A` / `D`：向左平移 / 向右平移
  - 或者使用 `↑` `↓` `←` `→` 方向键
- **转向控制**：
  - `Q` 或 `Z`：向左原地转向
  - `E` 或 `X`：向右原地转向

## 5. 其他快捷操作
- **■ Stop 功能**：在面板上还有一个红色的 **【■ Stop】** 按钮（等效于物理手柄的 `L2 + B`），点击后机器人会进入 Passive（被动/掉电）模式趴在地上。

---
*你可以利用控制面板中间的柱状条实时观察当前发送到 DDS 通信系统里的轴向控制数值。*
