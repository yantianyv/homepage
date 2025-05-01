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

# 获取系统架构信息
# 获取更详细的系统信息
SYS_NAME=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
OUTPUT_NAME="homepage_${SYS_NAME}_${ARCH}.bin"

# 使用 Nuitka 编译 Python 脚本
echo "正在编译..."
nuitka ./homepage.py \
    --standalone \
    --onefile \
    --jobs=$(nproc) \
    --lto=yes \
    --include-data-dir=static=static \
    --include-data-dir=templates=templates \
    --output-filename=${OUTPUT_NAME} \
    --output-dir=build \
    --remove-output