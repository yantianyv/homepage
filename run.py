import json
import os
from flask import Flask, render_template, redirect, send_from_directory, request, abort
from pathlib import Path
from datetime import datetime
import urllib.parse

app = Flask(__name__)

# 添加模板全局变量
@app.context_processor
def inject_globals():
    return {
        'now': datetime.now,
        'url_encode': urllib.parse.quote
    }

# 读取配置文件
with open('config.json', 'r', encoding='utf-8') as f:
    config_data = json.load(f)

# 安全地连接路径
def safe_join(base, *paths):
    base_path = Path(base).resolve()
    target_path = base_path.joinpath(*paths).resolve()
    
    # 确保目标路径在基础路径内
    try:
        target_path.relative_to(base_path)
        return target_path
    except ValueError:
        return None

# 获取文件图标类型
def get_file_icon(filename):
    if os.path.isdir(filename):
        return 'folder'
    
    extension = Path(filename).suffix.lower()
    icon_map = {
        '.pdf': 'file-pdf',
        '.zip': 'file-archive',
        '.rar': 'file-archive',
        '.7z': 'file-archive',
        '.tar': 'file-archive',
        '.gz': 'file-archive',
        '.doc': 'file-word',
        '.docx': 'file-word',
        '.xls': 'file-excel',
        '.xlsx': 'file-excel',
        '.ppt': 'file-powerpoint',
        '.pptx': 'file-powerpoint',
        '.txt': 'file-alt',
        '.md': 'file-alt',
        '.jpg': 'file-image',
        '.jpeg': 'file-image',
        '.png': 'file-image',
        '.gif': 'file-image',
        '.bmp': 'file-image',
        '.mp3': 'file-audio',
        '.wav': 'file-audio',
        '.mp4': 'file-video',
        '.avi': 'file-video',
        '.mov': 'file-video',
        '.exe': 'file-code',
        '.py': 'file-code',
        '.js': 'file-code',
        '.html': 'file-code',
        '.css': 'file-code',
        '.json': 'file-code'
    }
    return icon_map.get(extension, 'file')

# 格式化文件大小
def format_size(size):
    if size is None:  # 文件夹情况
        return ""
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

# 获取目录内容
def get_directory_contents(path=None):
    base_dir = os.path.join(app.root_path, 'static/files')
    
    # 处理路径安全
    if path:
        target_path = safe_join(base_dir, *path.split('/'))
        if not target_path or not target_path.exists():
            return None
    else:
        target_path = Path(base_dir)
    
    # 获取父目录路径（相对路径）
    parent_path = None
    if target_path != Path(base_dir):
        parent_path = str(target_path.parent.relative_to(base_dir))
    
    items = []
    for item in target_path.iterdir():
        is_dir = item.is_dir()
        stat = item.stat()
        
        items.append({
            'name': item.name,
            'path': str(item.relative_to(base_dir)).replace('\\', '/'),
            'is_dir': is_dir,
            'size': None if is_dir else stat.st_size,
            'formatted_size': format_size(None if is_dir else stat.st_size),
            'icon': get_file_icon(str(item)),
            'modified_time': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
            'description': "文件夹" if is_dir else f"{Path(item.name).suffix[1:].upper()}文件"
        })
    
    # 排序：文件夹在前，按名称排序
    items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
    
    return {
        'current_path': path,
        'parent_path': parent_path,
        'items': items
    }

# 首页路由
@app.route('/')
@app.route('/browse')
@app.route('/browse/<path:subpath>')
def browse(subpath=None):
    # 服务导航部分保持不变
    services = config_data['services']
    
    # 文件浏览部分
    directory = get_directory_contents(subpath)
    if directory is None:
        abort(404)
    
    return render_template(
        'index.html',
        services=services,
        directory=directory,
        site_title=config_data.get('site_title', '服务导航中心')
    )

# 文件下载路由
@app.route('/download/<path:filename>')
def download_file(filename):
    try:
        return send_from_directory(
            os.path.join(app.root_path, 'static/files'),
            filename,
            as_attachment=True
        )
    except FileNotFoundError:
        abort(404)

# 动态跳转路由
@app.route('/<service>')
def redirect_to_service(service):
    if service in config_data['services']:
        port = config_data['services'][service]['port']
        url = f"http://{domain}:{port}"
        return redirect(url)
    else:
        abort(404)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)