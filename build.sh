#!/bin/bash

# Install dependencies (Debian/Ubuntu)
DEPENDENCIES=("python3" "python3-venv" "python3-pip" "python3-dev" "gcc" "make" "ccache" "patchelf")
MISSING_DEPENDENCIES=()

for DEP in "${DEPENDENCIES[@]}"; do
    if ! dpkg -l | grep -qw "$DEP"; then
        MISSING_DEPENDENCIES+=("$DEP")
    fi
done

if [ ${#MISSING_DEPENDENCIES[@]} -ne 0 ]; then
    echo "Installing missing dependencies: ${MISSING_DEPENDENCIES[@]}"
    sudo apt install "${MISSING_DEPENDENCIES[@]}"
else
    echo "All dependencies installed."
fi

# Check and activate virtual environment
if [ -d "./venv" ]; then
    source ./venv/bin/activate
else
    echo "Creating virtual environment..."
    python3 -m venv venv
    source ./venv/bin/activate
    echo "Installing dependencies..."
    pip3 install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
fi

# Calculate jobs
if (( $(nproc) > 1 )); then
    MAX_JOBS=$(( $(nproc) - 1 ))
else
    MAX_JOBS=1
fi
echo "Using jobs: $MAX_JOBS"

# Output filename
SYS_NAME=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
OUTPUT_NAME="homepage_${SYS_NAME}_${ARCH}.bin"

# Build with Nuitka
echo "Building..."
nuitka ./run.py \
    --standalone \
    --onefile \
    --jobs=$MAX_JOBS \
    --lto=yes \
    --include-data-dir=static=static \
    --include-data-dir=templates=templates \
    --include-package=app \
    --include-package=scripts \
    --output-filename=${OUTPUT_NAME} \
    --output-dir=build

echo "Build complete! Output: build/${OUTPUT_NAME}"