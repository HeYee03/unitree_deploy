#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${REPO_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$REPO_DIR/.." && pwd)}"

SDK2_DIR="${SDK2_DIR:-$PROJECT_ROOT/unitree_sdk2}"
SDK2_PY_DIR="${SDK2_PY_DIR:-$PROJECT_ROOT/unitree_sdk2_python}"
CYCLONEDDS_DIR="${CYCLONEDDS_DIR:-$PROJECT_ROOT/cyclonedds}"

MUJOCO_VERSION="${MUJOCO_VERSION:-3.3.6}"
MUJOCO_ARCHIVE_DEFAULT="$HOME/Downloads/mujoco-${MUJOCO_VERSION}-linux-x86_64.tar.gz"
MUJOCO_ARCHIVE="${MUJOCO_ARCHIVE:-$MUJOCO_ARCHIVE_DEFAULT}"
MUJOCO_ROOT="${MUJOCO_ROOT:-$HOME/.mujoco}"
MUJOCO_EXTRACTED_DIR="${MUJOCO_EXTRACTED_DIR:-$MUJOCO_ROOT/mujoco-${MUJOCO_VERSION}}"

PYTHON_BIN="${PYTHON_BIN:-python}"
PIP_BIN="${PIP_BIN:-pip}"

G1_MESH_DIR="$REPO_DIR/unitree_mujoco/unitree_robots/g1/meshes"
G1_CTRL_CMAKE="$REPO_DIR/deploy/robots/g1_29dof/CMakeLists.txt"
G1_CTRL_BUILD_DIR="$REPO_DIR/deploy/robots/g1_29dof/build"

echo "Repo dir:        $REPO_DIR"
echo "Project root:    $PROJECT_ROOT"
echo "Python:          $PYTHON_BIN"
echo "Pip:             $PIP_BIN"
echo "MuJoCo archive:  $MUJOCO_ARCHIVE"
echo "MuJoCo root:     $MUJOCO_ROOT"
echo

if [ ! -d "$REPO_DIR" ]; then
  echo "Repository directory not found: $REPO_DIR"
  exit 1
fi

echo "[1/9] Installing apt dependencies..."
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

echo "[2/9] Installing unitree_sdk2 to /opt/unitree_robotics..."
if [ ! -d "$SDK2_DIR" ]; then
  git clone https://github.com/unitreerobotics/unitree_sdk2.git "$SDK2_DIR"
fi
mkdir -p "$SDK2_DIR/build"
cd "$SDK2_DIR/build"
cmake .. -DCMAKE_INSTALL_PREFIX=/opt/unitree_robotics -DBUILD_EXAMPLES=OFF
make -j"$(nproc)"
sudo make install

echo "[3/9] Building CycloneDDS..."
if [ ! -d "$CYCLONEDDS_DIR" ]; then
  git clone https://github.com/eclipse-cyclonedds/cyclonedds -b releases/0.10.x "$CYCLONEDDS_DIR"
fi
mkdir -p "$CYCLONEDDS_DIR/build" "$CYCLONEDDS_DIR/install"
cd "$CYCLONEDDS_DIR/build"
cmake .. -DCMAKE_INSTALL_PREFIX=../install
cmake --build . --target install -j"$(nproc)"

export CYCLONEDDS_HOME="$CYCLONEDDS_DIR/install"
export CMAKE_PREFIX_PATH="$CYCLONEDDS_HOME:/opt/unitree_robotics/lib/cmake:${CMAKE_PREFIX_PATH:-}"

echo "[4/9] Installing unitree_sdk2_python..."
if [ ! -d "$SDK2_PY_DIR" ]; then
  git clone https://github.com/unitreerobotics/unitree_sdk2_python.git "$SDK2_PY_DIR"
fi
cd "$SDK2_PY_DIR"
"$PIP_BIN" install -e .

echo "[5/9] Installing Python runtime packages..."
"$PIP_BIN" install mujoco pygame

echo "[6/9] Installing MuJoCo archive..."
if [ ! -f "$MUJOCO_ARCHIVE" ]; then
  echo "MuJoCo archive not found: $MUJOCO_ARCHIVE"
  echo "Download the official Linux package first, then rerun."
  echo "Example:"
  echo "  MUJOCO_ARCHIVE=\$HOME/Downloads/mujoco-${MUJOCO_VERSION}-linux-x86_64.tar.gz bash $0"
  exit 1
fi
mkdir -p "$MUJOCO_ROOT"
cp "$MUJOCO_ARCHIVE" "$MUJOCO_ROOT/"
cd "$MUJOCO_ROOT"
tar -xzf "$(basename "$MUJOCO_ARCHIVE")"

if [ ! -d "$MUJOCO_EXTRACTED_DIR" ]; then
  echo "Expected extracted MuJoCo directory not found: $MUJOCO_EXTRACTED_DIR"
  exit 1
fi

echo "[7/9] Checking G1 mesh assets..."
if [ ! -d "$G1_MESH_DIR" ]; then
  echo "Missing mesh directory: $G1_MESH_DIR"
  echo "Please make sure the repository includes unitree_mujoco/unitree_robots/g1/meshes"
  exit 1
fi

echo "[8/9] Patching deploy/robots/g1_29dof/CMakeLists.txt for /opt unitree_sdk2..."
"$PYTHON_BIN" - "$G1_CTRL_CMAKE" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()

if 'list(APPEND CMAKE_PREFIX_PATH "/opt/unitree_robotics/lib/cmake")' not in text:
    text = text.replace(
        'set(CMAKE_CXX_STANDARD 17)\n\n',
        'set(CMAKE_CXX_STANDARD 17)\n\nlist(APPEND CMAKE_PREFIX_PATH "/opt/unitree_robotics/lib/cmake")\nfind_package(unitree_sdk2 REQUIRED)\n'
    )

if '  /opt/unitree_robotics/include\n' not in text:
    text = text.replace(
        'include_directories(\n  /usr/include/eigen3\n',
        'include_directories(\n  /usr/include/eigen3\n  /opt/unitree_robotics/include\n'
    )

path.write_text(text)
PY

echo "[9/9] Building g1_ctrl..."
mkdir -p "$G1_CTRL_BUILD_DIR"
cd "$G1_CTRL_BUILD_DIR"
rm -f CMakeCache.txt
cmake ..
make -j"$(nproc)"

echo
echo "Verifying Python imports..."
"$PYTHON_BIN" -c "import mujoco, pygame, unitree_sdk2py; print('python imports ok')"

echo
echo "Setup complete."
echo
echo "Before running in a new terminal, set:"
echo "  export CYCLONEDDS_HOME=\"$CYCLONEDDS_DIR/install\""
echo "  export CMAKE_PREFIX_PATH=\"\$CYCLONEDDS_HOME:/opt/unitree_robotics/lib/cmake:\$CMAKE_PREFIX_PATH\""
echo
echo "Run simulator:"
echo "  cd \"$REPO_DIR/unitree_mujoco/simulate_python\""
echo "  $PYTHON_BIN unitree_mujoco.py"
echo
echo "Run controller in another terminal:"
echo "  cd \"$G1_CTRL_BUILD_DIR\""
echo "  ./g1_ctrl -n lo"
