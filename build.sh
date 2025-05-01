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

# 使用 Nuitka 编译 Python 脚本
echo "正在编译..."
nuitka ./homepage.py \
    --standalone \
    --onefile \
    --include-data-dir=static=static \
    --include-data-dir=templates=templates \
    --output-dir=build \
    --remove-output
