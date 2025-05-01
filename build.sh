nuitka ./homepage.py \
    --standalone\
    --onefile\
    --include-data-dir=static=static \
    --include-data-dir=templates=templates \
    --output-dir=build \
    --remove-output

