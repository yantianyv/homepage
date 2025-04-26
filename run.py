import json
import os
from flask import Flask, render_template, redirect, send_from_directory
from pathlib import Path
from datetime import datetime

app = Flask(__name__)


# 添加 now 函数到模板全局变量
@app.context_processor
def inject_now():
    return {"now": datetime.now}


# 读取配置文件
with open("config.json", "r", encoding="utf-8") as f:
    config_data = json.load(f)

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
    files = []
    for filename in os.listdir(files_dir):
        if filename == "descriptions.json":
            continue
        filepath = os.path.join(files_dir, filename)
        if os.path.isfile(filepath):
            stat = os.stat(filepath)
            files.append(
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
    # 按上传时间倒序排列
    files.sort(key=lambda x: x["upload_time"], reverse=True)
    return files


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
@app.route("/download/<filename>")
def download_file(filename):
    try:
        return send_from_directory(
            os.path.join(app.root_path, "static/files"), filename, as_attachment=True
        )
    except FileNotFoundError:
        return "文件不存在", 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
