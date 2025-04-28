import json
import os
from flask import Flask, get_flashed_messages, jsonify, render_template, redirect, send_from_directory, request, flash, url_for
from pathlib import Path
from datetime import datetime, timedelta
import set_cfg
from werkzeug.utils import secure_filename
import uuid
import platform

app = Flask(__name__)
app.secret_key = os.urandom(24)  # 用于flash消息


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

# 配置上传
UPLOAD_FOLDER = os.path.join(app.root_path, "static", "tempfiles")
FILES_FOLDER = os.path.join(app.root_path, "static", "files")
ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif", "zip", "rar", "7z", "doc", "docx", "xls", "xlsx", "ppt", "pptx"}

# 确保上传目录和文件目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(FILES_FOLDER, exist_ok=True)

# 配置大文件上传
# app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024 * 4  # 4GB限制
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_client_info():
    """获取客户端信息"""
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    user_agent = request.headers.get("User-Agent", "Unknown")
    system = platform.system()
    return {"ip": ip.split(",")[0].strip() if ip else "Unknown", "device": f"{system} - {user_agent.split('(')[1].split(')')[0]}" if "(" in user_agent else user_agent}


def cleanup_tempfiles():
    """清理超过24小时的临时文件"""
    now = datetime.now()
    for filename in os.listdir(UPLOAD_FOLDER):
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(filepath):
            stat = os.stat(filepath)
            file_time = datetime.fromtimestamp(stat.st_mtime)
            if (now - file_time) > timedelta(hours=24):
                try:
                    os.remove(filepath)
                    # 同时删除对应的描述文件
                    desc_file = os.path.join(UPLOAD_FOLDER, f".{filename}.json")
                    if os.path.exists(desc_file):
                        os.remove(desc_file)
                except Exception as e:
                    app.logger.error(f"Error deleting temp file {filename}: {e}")


def get_temp_files():
    """获取临时文件列表"""
    cleanup_tempfiles()  # 先清理过期文件
    files = []

    for filename in os.listdir(UPLOAD_FOLDER):
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(filepath) and not (filename.endswith(".json") and filename.startswith(".")):
            stat = os.stat(filepath)

            # 读取描述和上传者信息
            desc_file = os.path.join(UPLOAD_FOLDER, f".{filename}.json")
            description = "临时文件"
            uploader_info = {}
            original_filename = filename  # 保持原始文件名

            if os.path.exists(desc_file):
                try:
                    with open(desc_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        description = data.get("description", description)
                        uploader_info = data.get("uploader", {})
                        original_filename = data.get("original_filename", filename)  # 获取原始文件名
                except:
                    pass

            files.append(
                {
                    "name": original_filename,  # 显示原始文件名
                    "filename": f"tempfiles/{filename}",
                    "size": stat.st_size,
                    "formatted_size": format_size(stat.st_size),
                    "icon": get_file_icon(filename),
                    "upload_time": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                    "description": description,
                    "is_temp": True,
                    "uploader_ip": uploader_info.get("ip", "Unknown"),
                    "uploader_device": uploader_info.get("device", "Unknown"),
                }
            )

    # 按上传时间倒序排序
    files.sort(key=lambda x: x["upload_time"], reverse=True)
    return files


def get_file_icon(filename):
    # 定义不同图标对应的后缀列表
    icon_groups = {
        # 压缩包
        "file-zipper": [".zip", ".rar", ".7z"],
        "box": [".tar", ".xz", ".gz"],
        # 文档
        "file-pdf": [".pdf"],
        "file-word": [".doc", ".docx"],
        "file-excel": [".xls", ".xlsx"],
        "file-powerpoint": [".ppt", ".pptx"],
        "file-lines": [".txt"],
        "book": [".md"],
        # 媒体
        "file-image": [".jpg", ".jpeg", ".png", ".gif", "bmp", ""],
        "file-audio": [".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"],
        "file-video": [".mp4", ".avi", ".mkv", ".mov", ".flv", ".wmv", ".webm", ".3gp", ".mpg", ".mpeg", ".m4v", ".rmvb", ".rm"],
        # 可执行文件
        "cube": [".exe", ".bin", ".jar"],
        # 代码
        "file-code": [".py", ".c", ".cpp", ".java", ".html", ".css", ".js", ".json", ".xml", ".go", ".rs", ".swift", ".kt", ".rb", ".php"],
        "terminal": [".sh", ".bat"],
        # 数据库
        "database": [".accdb", ".db", ".sql", ".sqlite"],
    }
    extension = Path(filename).suffix.lower()

    # 遍历分组，查找对应图标
    for icon, extensions in icon_groups.items():
        if extension in extensions:
            return icon
    return "file"  # 默认图标


def format_size(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def get_downloadable_files():
    # 读取自定义描述
    desc_file = os.path.join(FILES_FOLDER, "descriptions.json")
    custom_descriptions = {}
    if os.path.exists(desc_file):
        with open(desc_file, "r", encoding="utf-8") as f:
            custom_descriptions = json.load(f)

    categories = {}

    # 遍历文件目录
    for root, dirs, files in os.walk(FILES_FOLDER):
        # 跳过根目录下的文件（直接放在files下的文件）
        if root == FILES_FOLDER:
            continue

        # 获取相对路径作为分类名
        rel_path = os.path.relpath(root, FILES_FOLDER)
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
                        "upload_time": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                        "description": custom_descriptions.get(filename, f"{Path(filename).suffix[1:].upper()}文件"),
                    }
                )

        if category_files:
            # 按文件名的首字母排序
            category_files.sort(key=lambda x: x["filename"][0])
            categories[category_name] = category_files

    # 处理根目录下的文件（无分类文件）
    root_files = []
    for filename in os.listdir(FILES_FOLDER):
        filepath = os.path.join(FILES_FOLDER, filename)
        if os.path.isfile(filepath) and filename != "descriptions.json":
            stat = os.stat(filepath)
            root_files.append(
                {
                    "name": filename,
                    "filename": filename,
                    "size": stat.st_size,
                    "formatted_size": format_size(stat.st_size),
                    "icon": get_file_icon(filename),
                    "upload_time": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                    "description": custom_descriptions.get(filename, f"{Path(filename).suffix[1:].upper()}文件"),
                }
            )

    if root_files:
        root_files.sort(key=lambda x: x["upload_time"], reverse=True)
        categories["未分类"] = root_files

    return categories


@app.route("/upload", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        # 检查是否有文件
        if "file" not in request.files:
            return jsonify({"success": False, "message": "没有选择文件"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"success": False, "message": "没有选择文件"}), 400

        if file and not os.path.isdir(file.filename):  # 检查是否是文件夹
            try:
                # 安全处理文件名
                filename = secure_filename(file.filename)
                original_filename = file.filename  # 保存原始文件名
                # 添加随机前缀避免冲突
                unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
                filepath = os.path.join(UPLOAD_FOLDER, unique_filename)

                # 使用流式写入处理大文件
                with open(filepath, "wb") as f:
                    # 分块读取文件内容并写入
                    while True:
                        chunk = file.stream.read(8192)  # 8KB的块
                        if not chunk:
                            break
                        f.write(chunk)

                # 获取描述信息，如果为空则使用默认值
                description = request.form.get("description", "").strip()
                if not description:
                    description = "上传者没有提供描述信息"

                # 保存描述和上传者信息
                desc_data = {"description": description, "uploader": get_client_info(), "upload_time": datetime.now().isoformat(), "original_filename": original_filename}

                with open(os.path.join(UPLOAD_FOLDER, f".{unique_filename}.json"), "w", encoding="utf-8") as f:
                    json.dump(desc_data, f, ensure_ascii=False, indent=2)

                return jsonify({"success": True, "message": "文件上传成功！"})
            except Exception as e:
                app.logger.error(f"Error uploading file: {e}")
                # 如果上传过程中出错，删除可能已部分上传的文件
                if os.path.exists(filepath):
                    os.remove(filepath)
                return jsonify({"success": False, "message": "文件上传失败"}), 500
        else:
            return jsonify({"success": False, "message": "不允许上传文件夹"}), 400

    # GET请求处理
    return render_template("upload.html", site_title=config_data.get("site_title", "服务导航中心"))


@app.route("/")
def index():
    return render_template("index.html", services=config_data["services"], downloads=get_downloadable_files(), temp_files=get_temp_files(), site_title=config_data.get("site_title", "服务导航中心"), show_upload=True)


@app.route("/<service>")
def redirect_to_service(service):
    if service in config_data["services"]:
        port = config_data["services"][service]["port"]
        url = f"http://{domain}:{port}"
        return redirect(url)
    else:
        return "服务未找到", 404


@app.route("/download/<path:filename>")
def download_file(filename):
    try:
        # 检查文件是否在files目录中
        filepath = os.path.join(FILES_FOLDER, filename)
        if os.path.exists(filepath):
            return send_from_directory(FILES_FOLDER, filename, as_attachment=True)

        # 检查文件是否在tempfiles目录中
        temp_filepath = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(temp_filepath):
            # 获取原始文件名
            desc_file = os.path.join(UPLOAD_FOLDER, f".{filename}.json")
            original_filename = filename
            if os.path.exists(desc_file):
                with open(desc_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    original_filename = data.get("original_filename", filename)

            return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True, download_name=original_filename)

        return "文件不存在", 404
    except Exception as e:
        app.logger.error(f"Error downloading file {filename}: {e}")
        return "下载文件时出错", 500


@app.route("/download/tempfiles/<filename>")
def download_tempfile(filename):
    try:
        # 获取原始文件名
        desc_file = os.path.join(UPLOAD_FOLDER, f".{filename}.json")
        original_filename = filename
        if os.path.exists(desc_file):
            with open(desc_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                original_filename = data.get("original_filename", filename)

        return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True, download_name=original_filename)
    except FileNotFoundError:
        return "文件不存在", 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
