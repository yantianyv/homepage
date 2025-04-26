import json
import os
from flask import Flask, render_template, redirect, send_from_directory
from pathlib import Path
from datetime import datetime
import set_cfg


app = Flask(__name__)


# 添加 now 函数到模板全局变量
@app.context_processor
def inject_now():
    return {"now": datetime.now}


# 读取配置文件
try:
    with open("config.json", "r", encoding="utf-8") as f:
        config_data = json.load(f)
except:
    set_cfg.main_menu()
# 获取域名配置
domain = config_data["domain"]


# 获取文件图标类型
def get_file_icon(filename):
    extension = Path(filename).suffix.lower()
    icon_map = {
        ".pdf": "file-pdf",
        ".zip": "file-archive",
        ".rar": "file-archive",
        ".doc": "file-word",
        ".docx": "file-word",
        ".xls": "file-excel",
        ".xlsx": "file-excel",
        ".ppt": "file-powerpoint",
        ".pptx": "file-powerpoint",
        ".txt": "file-alt",
        ".jpg": "file-image",
        ".jpeg": "file-image",
        ".png": "file-image",
        ".gif": "file-image",
        ".mp3": "file-audio",
        ".mp4": "file-video",
        ".exe": "file-code",
    }
    return icon_map.get(extension, "file")


# 格式化文件大小
def format_size(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


# 获取可下载文件列表
def get_downloadable_files():
    # 读取自定义描述
    desc_file = os.path.join(app.root_path, "static/files/descriptions.json")
    custom_descriptions = {}
    if os.path.exists(desc_file):
        with open(desc_file, "r", encoding="utf-8") as f:
            custom_descriptions = json.load(f)

    files_dir = os.path.join(app.root_path, "static/files")
    categories = {}

    # 遍历文件目录
    for root, dirs, files in os.walk(files_dir):
        # 跳过根目录下的文件（直接放在files下的文件）
        if root == files_dir:
            continue

        # 获取相对路径作为分类名
        rel_path = os.path.relpath(root, files_dir)
        if rel_path == ".":
            continue

        category_name = rel_path.replace(os.sep, " / ")
        category_files = []

        for filename in files:
            if filename == "descriptions.json":
                continue

            filepath = os.path.join(root, filename)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                category_files.append(
                    {
                        "name": filename,
                        "filename": os.path.join(rel_path, filename),  # 包含相对路径
                        "size": stat.st_size,
                        "formatted_size": format_size(stat.st_size),
                        "icon": get_file_icon(filename),
                        "upload_time": datetime.fromtimestamp(stat.st_mtime).strftime(
                            "%Y-%m-%d %H:%M"
                        ),
                        "description": custom_descriptions.get(
                            filename, f"{Path(filename).suffix[1:].upper()}文件"
                        ),
                    }
                )

        if category_files:
            # 按文件名的首字母排序
            category_files.sort(key=lambda x: x["filename"][0])
            categories[category_name] = category_files

    # 处理根目录下的文件（无分类文件）
    root_files = []
    for filename in os.listdir(files_dir):
        filepath = os.path.join(files_dir, filename)
        if os.path.isfile(filepath) and filename != "descriptions.json":
            stat = os.stat(filepath)
            root_files.append(
                {
                    "name": filename,
                    "filename": filename,
                    "size": stat.st_size,
                    "formatted_size": format_size(stat.st_size),
                    "icon": get_file_icon(filename),
                    "upload_time": datetime.fromtimestamp(stat.st_mtime).strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                    "description": custom_descriptions.get(
                        filename, f"{Path(filename).suffix[1:].upper()}文件"
                    ),
                }
            )

    if root_files:
        root_files.sort(key=lambda x: x["upload_time"], reverse=True)
        categories["未分类"] = root_files

    return categories


# 首页路由
@app.route("/")
def index():
    return render_template(
        "index.html",
        services=config_data["services"],
        downloads=get_downloadable_files(),
        site_title=config_data.get("site_title", "服务导航中心"),
    )


# 动态跳转路由
@app.route("/<service>")
def redirect_to_service(service):
    if service in config_data["services"]:
        port = config_data["services"][service]["port"]
        url = f"http://{domain}:{port}"
        return redirect(url)
    else:
        return "服务未找到", 404


# 文件下载路由
@app.route("/download/<path:filename>")
def download_file(filename):
    try:
        return send_from_directory(
            os.path.join(app.root_path, "static/files"), filename, as_attachment=True
        )
    except FileNotFoundError:
        return "文件不存在", 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
