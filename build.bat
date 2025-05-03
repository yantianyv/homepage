@echo off
setlocal enabledelayedexpansion

:: 检查并激活虚拟环境
if exist ".\venv\" (
    call .\venv\Scripts\activate
) else (
    echo 正在创建虚拟环境...
    python -m venv venv
    call .\venv\Scripts\activate
    echo 正在安装依赖项，请确保网络通畅...
    pip install -r requirements.txt
)

:: 获取系统信息
for /f "tokens=*" %%a in ('ver') do set OS_VER=%%a
set SYS_NAME=win
set OUTPUT_NAME=homepage_%SYS_NAME%.exe

:: 使用 Nuitka 编译 Python 脚本
echo 正在编译...
python -m nuitka homepage.py ^
    --standalone ^
    --onefile ^
    --jobs=%NUMBER_OF_PROCESSORS%-1 ^
    --lto=no ^
    --include-data-dir=static=static ^
    --include-data-dir=templates=templates ^
    --output-filename=%OUTPUT_NAME% ^
    --output-dir=build
endlocal