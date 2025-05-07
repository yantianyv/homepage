#!/bin/bash

# 安装依赖项（Debian）
DEPENDENCIES=("python3" "python3-venv" "python3-pip" "python3-dev" "gcc" "make" "ccache" "patchelf")
MISSING_DEPENDENCIES=()

for DEP in "${DEPENDENCIES[@]}"; do
    if ! dpkg -l | grep -qw "$DEP"; then
        MISSING_DEPENDENCIES+=("$DEP")
    fi
done

if [ ${#MISSING_DEPENDENCIES[@]} -ne 0 ]; then
    echo "正在安装缺失的依赖项: ${MISSING_DEPENDENCIES[@]}"
    sudo apt install "${MISSING_DEPENDENCIES[@]}"
else
    echo "所有依赖项都已安装。"
fi

# 检查并激活虚拟环境
if [ -d "./venv" ]; then
    source ./venv/bin/activate
else
    echo "正在创建虚拟环境..."
    python3 -m venv venv
    source ./venv/bin/activate
    echo "正在安装依赖项，请确保网络通畅..."
    pip3 install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
fi

# 动态计算并发任务数（保留至少1核心）
if (( $(nproc) > 1 )); then
    MAX_JOBS=$(( $(nproc) - 1 ))
else
    MAX_JOBS=1
fi
echo "使用并发任务数: $MAX_JOBS"

# 编译输出文件名
SYS_NAME=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
OUTPUT_NAME="homepage_${SYS_NAME}_${ARCH}.bin"

# 使用 Nuitka 编译
echo "正在编译..."
nuitka ./homepage.py \
    --standalone \
    --onefile \
    --jobs=$MAX_JOBS \
    --lto=yes \
    --include-data-dir=static=static \
    --include-data-dir=templates=templates \
    --output-filename=${OUTPUT_NAME} \
    --output-dir=build

echo "编译完成！输出文件: build/${OUTPUT_NAME}"