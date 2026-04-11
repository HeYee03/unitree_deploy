# Unitree Deploy 服务器部署说明

本文档面向已经具备 Isaac Lab Python 环境的服务器用户，目标是快速完成 `unitree_deploy` 的 G1-29dof 仿真部署，并使用虚拟手柄界面运行 `sim-to-sim`。

## 1. 前提条件

- 已有可用的 Isaac Lab / Conda Python 环境
- 服务器具备图形显示能力，可以正常弹出 MuJoCo 和 Pygame 窗口
- 已经下载官方 MuJoCo Linux 安装包，例如：
  `mujoco-3.3.6-linux-x86_64.tar.gz`

## 2. 仓库目录约定

推荐把仓库放到任意你有权限的位置。文档里的命令默认使用：

```bash
export PROJECT_ROOT=$HOME/project
export REPO_DIR=$PROJECT_ROOT/unitree_deploy
```

如果你的实际路径不同，请自行替换。

## 3. 克隆仓库

```bash
mkdir -p $PROJECT_ROOT
cd $PROJECT_ROOT
git clone https://github.com/HeYee03/unitree_deploy.git
cd $REPO_DIR
```

## 4. 准备 Python 环境

激活你已有的 Isaac Lab 环境，例如：

```bash
conda activate env_isaaclab
```

建议切换到国内源：

```bash
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

## 5. 安装系统依赖

```bash
sudo apt update
sudo apt install -y \
  build-essential \
  cmake \
  git \
  libyaml-cpp-dev \
  libboost-all-dev \
  libeigen3-dev \
  libspdlog-dev \
  libfmt-dev \
  libglfw3-dev
```

## 6. 安装 unitree_sdk2 到 /opt

```bash
cd $PROJECT_ROOT
git clone https://github.com/unitreerobotics/unitree_sdk2.git
cd unitree_sdk2
mkdir -p build
cd build
cmake .. -DCMAKE_INSTALL_PREFIX=/opt/unitree_robotics -DBUILD_EXAMPLES=OFF
make -j$(nproc)
sudo make install
```

## 7. 安装 CycloneDDS

```bash
cd $PROJECT_ROOT
git clone https://github.com/eclipse-cyclonedds/cyclonedds -b releases/0.10.x
cd cyclonedds
mkdir -p build install
cd build
cmake .. -DCMAKE_INSTALL_PREFIX=../install
cmake --build . --target install -j$(nproc)
```

设置环境变量：

```bash
export CYCLONEDDS_HOME=$PROJECT_ROOT/cyclonedds/install
export CMAKE_PREFIX_PATH=$CYCLONEDDS_HOME:/opt/unitree_robotics/lib/cmake:$CMAKE_PREFIX_PATH
```

## 8. 安装 unitree_sdk2_python 与 Python 依赖

```bash
cd $PROJECT_ROOT
git clone https://github.com/unitreerobotics/unitree_sdk2_python.git
cd unitree_sdk2_python
pip install -e .

pip install mujoco pygame
```

验证：

```bash
python -c "import mujoco, pygame, unitree_sdk2py; print('ok')"
```

## 9. 安装 MuJoCo

将你下载好的官方安装包放到任意可访问路径，例如：

```bash
$HOME/Downloads/mujoco-3.3.6-linux-x86_64.tar.gz
```

解压到 `$HOME/.mujoco`：

```bash
mkdir -p $HOME/.mujoco
cp $HOME/Downloads/mujoco-3.3.6-linux-x86_64.tar.gz $HOME/.mujoco/
cd $HOME/.mujoco
tar -xzf mujoco-3.3.6-linux-x86_64.tar.gz
```

## 10. 确认 G1 meshes 资源已在仓库中

该版本仓库已经直接包含：

```bash
unitree_mujoco/unitree_robots/g1/meshes
```

执行检查：

```bash
ls $REPO_DIR/unitree_mujoco/unitree_robots/g1/meshes | head
```

## 11. 修正 g1_ctrl 编译配置

编辑：

`deploy/robots/g1_29dof/CMakeLists.txt`

确保包含以下两项：

```cmake
list(APPEND CMAKE_PREFIX_PATH "/opt/unitree_robotics/lib/cmake")
find_package(unitree_sdk2 REQUIRED)
```

并在 `include_directories(...)` 中加入：

```cmake
/opt/unitree_robotics/include
```

## 12. 编译 g1_ctrl

```bash
cd $REPO_DIR/deploy/robots/g1_29dof
mkdir -p build
cd build
cmake ..
make -j$(nproc)
```

## 13. 检查 Python 仿真配置

文件：

`unitree_mujoco/simulate_python/config.py`

建议至少确认以下内容：

```python
ROBOT = "g1"
ROBOT_SCENE = "../unitree_robots/" + ROBOT + "/scene_29dof.xml"
DOMAIN_ID = 0
INTERFACE = "lo"
USE_JOYSTICK = 0
USE_KEYBOARD = True
ENABLE_ELASTIC_BAND = True
```

## 14. 启动方式

需要两个终端。

终端 1：

```bash
conda activate env_isaaclab
export PROJECT_ROOT=$HOME/project
export CYCLONEDDS_HOME=$PROJECT_ROOT/cyclonedds/install
export CMAKE_PREFIX_PATH=$CYCLONEDDS_HOME:/opt/unitree_robotics/lib/cmake:$CMAKE_PREFIX_PATH
cd $PROJECT_ROOT/unitree_deploy/unitree_mujoco/simulate_python
python unitree_mujoco.py
```

终端 2：

```bash
conda activate env_isaaclab
cd $HOME/project/unitree_deploy/deploy/robots/g1_29dof/build
./g1_ctrl -n lo
```

## 15. 操作顺序

1. 在 `Virtual Controller` 窗口点击 `▲ Stand`
2. 切换到 MuJoCo 窗口，按键盘 `8`
3. 回到 `Virtual Controller`，点击 `▶ Walk`
4. 切换到 MuJoCo 窗口，按键盘 `9`

进入行走模式后：

- `W/S/A/D` 或方向键控制平移
- `Q/E/Z/X` 控制转向
- 点击 `■ Stop` 可切回 Passive

## 16. 常见问题

### 1. `ModuleNotFoundError: No module named 'mujoco'`

执行：

```bash
pip install mujoco pygame
```

### 2. `Could not locate cyclonedds`

说明 `unitree_sdk2_python` 安装时找不到本地 CycloneDDS，确认以下环境变量：

```bash
export CYCLONEDDS_HOME=$PROJECT_ROOT/cyclonedds/install
export CMAKE_PREFIX_PATH=$CYCLONEDDS_HOME:/opt/unitree_robotics/lib/cmake:$CMAKE_PREFIX_PATH
```

然后重新执行：

```bash
cd $PROJECT_ROOT/unitree_sdk2_python
pip install -e .
```

### 3. `Error opening file 'unitree_robots/g1/...STL'`

说明仓库里缺少 `unitree_robots/g1/meshes` 目录，或 meshes 没有被正确推送。

### 4. `fatal error: unitree/dds_wrapper/...: No such file or directory`

说明 `deploy/robots/g1_29dof/CMakeLists.txt` 没有包含 `/opt/unitree_robotics/include`。

## 17. 自动化执行方式

如果仓库里已经包含 `g1/meshes`，可以按下面方式部署：

1. 激活已有环境

```bash
conda activate env_isaaclab
```

2. 克隆仓库

```bash
mkdir -p $HOME/project
cd $HOME/project
git clone https://github.com/HeYee03/unitree_deploy.git
```

3. 确保 MuJoCo 安装包放在：

```bash
$HOME/Downloads/mujoco-3.3.6-linux-x86_64.tar.gz
```

4. 运行脚本

```bash
bash unitree_deploy/scripts/setup_server_g1_virtual_controller.sh
```
