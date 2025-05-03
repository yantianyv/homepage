@echo off
setlocal enabledelayedexpansion

:: ��鲢�������⻷��
if exist ".\venv\" (
    call .\venv\Scripts\activate
) else (
    echo ���ڴ������⻷��...
    python -m venv venv
    call .\venv\Scripts\activate
    echo ���ڰ�װ�������ȷ������ͨ��...
    pip install -r requirements.txt
)

:: �����߳���
set /a MAX_JOBS=%NUMBER_OF_PROCESSORS%-1
if %MAX_JOBS% lss 1 set MAX_JOBS=1

:: ��ȡϵͳ��Ϣ
for /f "tokens=*" %%a in ('ver') do set OS_VER=%%a
set SYS_NAME=win
set OUTPUT_NAME=homepage_%SYS_NAME%.exe

:: ʹ�� Nuitka ���� Python �ű�
echo ���ڱ���...
python -m nuitka homepage.py ^
    --standalone ^
    --onefile ^
    --jobs=%MAX_JOBS% ^
    --lto=no ^
    --include-data-dir=static=static ^
    --include-data-dir=templates=templates ^
    --output-filename=%OUTPUT_NAME% ^
    --output-dir=build
endlocal