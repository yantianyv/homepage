import json
import os
import sys
from flask import Flask, jsonify, render_template, redirect, request, send_from_directory
from pathlib import Path
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import uuid
import platform
from scripts import get_favicon, set_cfg
import threading
import time

PORT = 80
config_data = {}  # 全局配置变量

def load_config():
    global config_data,default_domain
    # 读取配置文件
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config_data = json.load(f)
    except:
        set_cfg.main_menu()
        os.makedirs(UPLOAD_PATH, exist_ok=True)
        os.makedirs(FILES_PATH, exist_ok=True)
        with open("config.json", "r", encoding="utf-8") as f:
            config_data = json.load(f)

    default_domain = config_data.get("default_domain", "127.0.0.1")
    if config_data.get("shutdown"):
        print("服务被关闭")
        os._exit(0)

# 获取启动参数
if len(sys.argv) > 1:
    # help
    if sys.argv[1] == "--help" or sys.argv[1] == "-h":
        help_text = f"""
        Usage: python homepage.py [options]
        Options:
        -h, --help            Show this help message
        -s, --set            Set configuration
        -p, --port PORT       Run with specified port (default: {PORT})
        --shutdown            Shutdown server
        """
        print(help_text)
        sys.exit(0)
    
    # set
    elif sys.argv[1] == "--set" or sys.argv[1] == "-s":
        set_cfg.main_menu()
        sys.exit(0)
    
    # port
    elif sys.argv[1] == "--port" or sys.argv[1] == "-p":
        if len(sys.argv) > 2:
            PORT = int(sys.argv[2])
        else:
            print("Error: Port number not specified. Using default port 80.")
    
    # shutdown
    elif sys.argv[1] == "--shutdown":
        with open("config.json", "r", encoding="utf-8") as f:
            config_data = json.load(f)
        config_data["shutdown"] = True
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
        print("服务器通常会在1分钟内关闭")
        sys.exit(0)
    
    # unknown option
    else:
        print(f"Unknown option: {sys.argv[1]}")
        sys.exit(1)  # 非零退出码表示错误

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.urandom(24)

@app.context_processor
def inject_now():
    return {"now": datetime.now}

if "__compiled__" in globals():
    print("检测到当前运行的是使用nuitka打包后的二进制文件")
    if os.name == "posix":
        BASE_DIR = os.getcwd()
        if os.getuid() != 0 and PORT<1024:
            print("Linux系统中，小于1024的端口可能需要sudo权限。")
    else:
        BASE_DIR = os.path.dirname(sys.executable) # Nuitka/ PyInstaller 单文件模式
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FILES_PATH = os.path.join(BASE_DIR, "files")
UPLOAD_FOLDER = ".tempfiles"
UPLOAD_PATH = os.path.join(BASE_DIR, FILES_PATH, UPLOAD_FOLDER)
print(f"FILES_PATH: {FILES_PATH} \nUPLOAD_PATH: {UPLOAD_PATH}")

# 确保目录存在
os.makedirs(UPLOAD_PATH, exist_ok=True)
os.makedirs(FILES_PATH, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_PATH

try:
    # 重置关闭参数
    with open("config.json", "r", encoding="utf-8") as f:
        config_data = json.load(f)
    config_data["shutdown"] = False
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=4)
except:
    pass

# 加载配置文件
load_config()


def get_client_info():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    user_agent = request.headers.get("User-Agent", "Unknown")
    system = platform.system()
    return {"ip": ip.split(",")[0].strip() if ip else "Unknown", "device": f"{system} - {user_agent.split('(')[1].split(')')[0]}" if "(" in user_agent else user_agent}


def cleanup_tempfiles():
    now = datetime.now()
    for filename in os.listdir(UPLOAD_PATH):
        filepath = os.path.join(UPLOAD_PATH, filename)
        if os.path.isfile(filepath):
            stat = os.stat(filepath)
            file_time = datetime.fromtimestamp(stat.st_mtime)
            if (now - file_time) > timedelta(hours=24):
                try:
                    os.remove(filepath)
                    desc_file = os.path.join(UPLOAD_PATH, f".{filename}.json")
                    if os.path.exists(desc_file):
                        os.remove(desc_file)
                except Exception as e:
                    app.logger.error(f"Error deleting temp file {filename}: {e}")


def get_temp_files():
    cleanup_tempfiles()
    files = []
    for filename in os.listdir(UPLOAD_PATH):
        filepath = os.path.join(UPLOAD_PATH, filename)
        if os.path.isfile(filepath) and not filename.startswith("."):
            stat = os.stat(filepath)
            desc_file = os.path.join(UPLOAD_PATH, f".{filename}.json")
            description = "临时文件"
            uploader_info = {}
            original_filename = filename

            if os.path.exists(desc_file):
                try:
                    with open(desc_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        description = data.get("description", description)
                        uploader_info = data.get("uploader", {})
                        original_filename = data.get("original_filename", filename)
                except:
                    pass

            files.append(
                {
                    "name": original_filename,
                    "filename": f"{UPLOAD_FOLDER}/{filename}",
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

    files.sort(key=lambda x: x["upload_time"], reverse=True)
    return files


def get_file_icon(filename):
    icon_groups = {
        "file-zipper": [".zip", ".rar", ".7z"],
        "box": [".tar", ".xz", ".gz"],
        "file-pdf": [".pdf"],
        "file-word": [".doc", ".docx"],
        "file-excel": [".xls", ".xlsx"],
        "file-powerpoint": [".ppt", ".pptx"],
        "file-lines": [".txt"],
        "book": [".md"],
        "file-image": [".jpg", ".jpeg", ".png", ".gif", "bmp"],
        "file-audio": [".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"],
        "file-video": [".mp4", ".avi", ".mkv", ".mov", ".flv", ".wmv", ".webm"],
        "cube": [".exe", ".bin", ".jar"],
        "file-code": [".py", ".c", ".cpp", ".java", ".html", ".css", ".js"],
        "terminal": [".sh", ".bat"],
        "database": [".accdb", ".db", ".sql", ".sqlite"],
    }
    extension = Path(filename).suffix.lower()
    for icon, extensions in icon_groups.items():
        if extension in extensions:
            return icon
    return "file"


def format_size(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def get_downloadable_files():
    desc_file = os.path.join(FILES_PATH, "descriptions.json")
    custom_descriptions = {}
    if os.path.exists(desc_file):
        with open(desc_file, "r", encoding="utf-8") as f:
            custom_descriptions = json.load(f)

    categories = {}
    for root, dirs, files in os.walk(FILES_PATH):
        dirs.sort()
        if root == FILES_PATH:
            continue

        rel_path = os.path.relpath(root, FILES_PATH)
        if rel_path == ".":
            continue

        if rel_path == UPLOAD_FOLDER:
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
                        "filename": os.path.join(rel_path, filename),
                        "size": stat.st_size,
                        "formatted_size": format_size(stat.st_size),
                        "icon": get_file_icon(filename),
                        "upload_time": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                        "description": custom_descriptions.get(filename, f"{Path(filename).suffix[1:].upper()}文件"),
                    }
                )

        if category_files:
            category_files.sort(key=lambda x: x["filename"][0])
            categories[category_name] = category_files

    root_files = []
    for filename in os.listdir(FILES_PATH):
        filepath = os.path.join(FILES_PATH, filename)
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

@app.route("/")
def index():
    # 为每个服务添加域名信息
    services_with_domains = {}
    for service_id, service_info in config_data["services"].items():
        service_with_domain = service_info.copy()
        service_with_domain["domain"] = service_info.get("domain", default_domain)
        services_with_domains[service_id] = service_with_domain

    return render_template("index.html", services=services_with_domains, downloads=get_downloadable_files(), temp_files=get_temp_files(), site_title=config_data.get("site_title", "服务导航中心"), show_upload=True)


@app.route("/<service>")
def redirect_to_service(service):
    if service in config_data["services"]:
        service_info = config_data["services"][service]
        port = service_info["port"]
        domain = service_info.get("domain", default_domain)
        return redirect(f"http://{domain}:{port}")
    return "服务未找到", 404

@app.route("/favicon/<service_id>")
def get_service_favicon(service_id):
    """返回指定服务的favicon图标"""
    try:
        app.logger.debug(f"Requested favicon for service: {service_id}")
        
        # 检查服务是否存在
        if service_id not in config_data["services"]:
            app.logger.error(f"Service not found: {service_id}")
            return "Service not found", 404
        
        # 获取服务的favicon文件名
        favicon_name = config_data["services"][service_id].get("favicon")
        if not favicon_name:
            app.logger.error(f"No favicon configured for service: {service_id}")
            return "Favicon not configured for this service", 404
        
        app.logger.debug(f"Favicon filename: {favicon_name}")
        
        # 构建favicon文件路径
        favicon_path = os.path.join(BASE_DIR, "favicons", favicon_name)
        app.logger.debug(f"Full favicon path: {favicon_path}")
        
        # 检查文件是否存在
        if not os.path.exists(favicon_path):
            app.logger.error(f"Favicon file not found at: {favicon_path}")
            return "Favicon file not found", 404
        
        # 根据文件扩展名设置正确的MIME类型
        _, ext = os.path.splitext(favicon_name.lower())
        mime_types = {
            '.ico': 'image/x-icon',
            '.svg': 'image/svg+xml',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif'
        }
        mimetype = mime_types.get(ext, 'application/octet-stream')
        app.logger.debug(f"Detected MIME type: {mimetype} for extension {ext}")
        
        # 发送文件
        app.logger.info(f"Serving favicon for {service_id}: {favicon_name}")
        return send_from_directory(
            directory=os.path.join(BASE_DIR, "favicons"),
            path=favicon_name,
            mimetype=mimetype
        )
        
    except Exception as e:
        app.logger.error(f"Error serving favicon for {service_id}: {str(e)}", exc_info=True)
        return "Internal server error", 500

@app.route("/upload", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        if "file" not in request.files:
            return jsonify({"success": False, "message": "没有选择文件"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"success": False, "message": "没有选择文件"}), 400

        if file and not os.path.isdir(file.filename):
            try:
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
                filepath = os.path.join(UPLOAD_PATH, unique_filename)

                with open(filepath, "wb") as f:
                    while True:
                        chunk = file.stream.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)

                description = request.form.get("description", "").strip() or "上传者没有提供描述信息"
                desc_data = {"description": description, "uploader": get_client_info(), "upload_time": datetime.now().isoformat(), "original_filename": file.filename}

                with open(os.path.join(UPLOAD_PATH, f".{unique_filename}.json"), "w", encoding="utf-8") as f:
                    json.dump(desc_data, f, ensure_ascii=False, indent=2)

                return jsonify({"success": True, "message": "文件上传成功！"})
            except Exception as e:
                app.logger.error(f"Error uploading file: {e}")
                if os.path.exists(filepath):
                    os.remove(filepath)
                return jsonify({"success": False, "message": "文件上传失败"}), 500
        else:
            return jsonify({"success": False, "message": "不允许上传文件夹"}), 400

    return render_template("upload.html", site_title=config_data.get("site_title", "服务导航中心"))

@app.route("/download/<path:filepath>")
def download_file(filepath):
    print("filepath:", filepath)
    try:
        filepath = os.path.normpath(filepath)  # 统一转为系统路径格式
        filename = os.path.basename(filepath)  # 提取纯文件名
        file_dir = os.path.dirname(filepath)   # 提取目录部分
        full_path = os.path.join(FILES_PATH, filepath)

        # 如果filepath对应的文件存在
        if os.path.exists(full_path):
            desc_file = os.path.join(UPLOAD_PATH, f".{filename}.json")
            original_filename = filepath
            
            # 处理临时文件
            if os.path.exists(desc_file):
                with open(desc_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    original_filename = data.get("original_filename")
                    print("\n"+original_filename)
                print("识别为临时文件")
                print(f"下载目录: {FILES_PATH}， 文件路径: {filepath}")
                return send_from_directory(os.path.join(FILES_PATH, file_dir), filename, 
                                             as_attachment=True, download_name=original_filename)
            # 处理长期文件
            else:
                # 非根目录下的文件
                if file_dir:
                    return send_from_directory(os.path.join(FILES_PATH, file_dir), filename, 
                                            as_attachment=True)
                #根目录下的文件
                else:
                    return send_from_directory(FILES_PATH, filename, 
                                          as_attachment=True)
        else:
            print(f"文件{full_path}不存在")
            return "文件不存在", 404
    except Exception as e:
        app.logger.error(f"Error downloading file {filepath}: {e}")
        print(f"文件{os.path.join(FILES_PATH, filepath)}下载出错")
        return "下载文件时出错", 500

def refresh_favicon_and_config():
    while True:
        try:
            get_favicon.refresh()
        except Exception as e:
            print(f"刷新图标出错: {e}")
        for _ in range(60):
            try:
                load_config()
            except Exception as e:
                print(f"加载配置出错: {e}")
            time.sleep(1)

if __name__ == "__main__":
    load_config()
    # 设置守护线程，这样主程序退出时它也退出
    refresh_thread = threading.Thread(
        target=refresh_favicon_and_config, 
        daemon=True  # ← 关键设置
    )
    refresh_thread.start()

    # 捕获 Flask 启动异常，确保失败时整个程序退出
    try:
        app.run(host="0.0.0.0", port=PORT)
    except Exception as e:
        print(f"Flask 启动失败: {e}")
        os._exit(1)  # ← 强制整个进程退出

