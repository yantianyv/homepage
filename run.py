import json
import os
from flask import Flask, render_template, redirect, send_from_directory
from pathlib import Path

app = Flask(__name__)

# 读取配置文件
with open("config.json", "r", encoding="utf-8") as f:
    config_data = json.load(f)

# 获取域名配置
domain = config_data["domain"]


# 获取可下载文件列表
def get_downloadable_files():
    files_dir = os.path.join(app.root_path, "static/files")
    files = []
    for filename in os.listdir(files_dir):
        filepath = os.path.join(files_dir, filename)
        if os.path.isfile(filepath):
            files.append(
                {
                    "name": filename,
                    "filename": filename,
                    "size": os.path.getsize(filepath),
                    "description": f"{filename} ({Path(filename).suffix[1:].upper()}文件)",
                }
            )
    return files


# 首页路由
@app.route("/")
def index():
    return render_template(
        "index.html",
        services=config_data["services"],
        downloads=get_downloadable_files(),
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
