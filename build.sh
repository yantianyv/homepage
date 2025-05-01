if [ -d "./venv" ]; then
    source ./venv/bin/activate
else
    echo "正在创建虚拟环境..."
    python -m venv venv
    source ./venv/bin/activate
    pip install -r requirements.txt
nuitka ./homepage.py \
    --standalone\
    --onefile\
    --include-data-dir=static=static \
    --include-data-dir=templates=templates \
    --output-dir=build \
    --remove-output

