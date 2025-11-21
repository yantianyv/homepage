@echo off
setlocal enabledelayedexpansion

:: Check virtual environment
if exist ".\venv\" (
    call .\venv\Scripts\activate
) else (
    echo Creating virtual environment...
    python -m venv venv
    call .\venv\Scripts\activate
    echo Installing dependencies...
    pip install -r requirements.txt
)

:: Threads
set /a MAX_JOBS=%NUMBER_OF_PROCESSORS%-1
if %MAX_JOBS% lss 1 set MAX_JOBS=1

:: System info
set SYS_NAME=win
set OUTPUT_NAME=homepage_%SYS_NAME%.exe

:: Build with Nuitka
echo Building...
python -m nuitka run.py ^
    --standalone ^
    --onefile ^
    --jobs=%MAX_JOBS% ^
    --lto=no ^
    --include-data-dir=static=static ^
    --include-data-dir=templates=templates ^
    --include-package=app ^
    --include-package=scripts ^
    --output-filename=%OUTPUT_NAME% ^
    --output-dir=build
endlocal