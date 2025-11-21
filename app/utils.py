import os
import json
import platform
from datetime import datetime, timedelta
from pathlib import Path
from flask import request
from app.config import UPLOAD_PATH, FILES_PATH, UPLOAD_FOLDER

def get_client_info():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    user_agent = request.headers.get("User-Agent", "Unknown")
    system = platform.system()
    device_info = user_agent
    if "(" in user_agent:
        try:
            device_info = f"{system} - {user_agent.split('(')[1].split(')')[0]}"
        except IndexError:
            pass
            
    return {
        "ip": ip.split(",")[0].strip() if ip else "Unknown", 
        "device": device_info
    }

def format_size(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

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

def cleanup_tempfiles(logger=None):
    now = datetime.now()
    if not os.path.exists(UPLOAD_PATH):
        return
        
    for filename in os.listdir(UPLOAD_PATH):
        filepath = os.path.join(UPLOAD_PATH, filename)
        if os.path.isfile(filepath):
            try:
                stat = os.stat(filepath)
                file_time = datetime.fromtimestamp(stat.st_mtime)
                if (now - file_time) > timedelta(hours=24):
                    os.remove(filepath)
                    desc_file = os.path.join(UPLOAD_PATH, f".{filename}.json")
                    if os.path.exists(desc_file):
                        os.remove(desc_file)
            except Exception as e:
                if logger:
                    logger.error(f"Error deleting temp file {filename}: {e}")

def get_temp_files():
    cleanup_tempfiles()
    files = []
    if not os.path.exists(UPLOAD_PATH):
        return files
        
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

def get_downloadable_files():
    desc_file = os.path.join(FILES_PATH, "descriptions.json")
    custom_descriptions = {}
    if os.path.exists(desc_file):
        try:
            with open(desc_file, "r", encoding="utf-8") as f:
                custom_descriptions = json.load(f)
        except:
            pass

    categories = {}
    if not os.path.exists(FILES_PATH):
        return categories

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
