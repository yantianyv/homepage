#!/bin/bash

# 检查并激活虚拟环境
if [ -d "./venv" ]; then
    source ./venv/bin/activate
else
    echo "正在创建虚拟环境..."
    python -m venv venv
    source ./venv/bin/activate
    echo "正在安装依赖项，请确保网络通畅..."
    pip install -r requirements.txt
fi

# 动态计算并发任务数（保留至少1核心）
MAX_JOBS=$(($(nproc) > 1 ? $(nproc) - 1 : 1))
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