import json
import os
import requests
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import ssl
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 配置路径
CONFIG_PATH = "config.json"
FAVICON_DIR = "favicons"

# 确保 favicons 目录存在
os.makedirs(FAVICON_DIR, exist_ok=True)

# 创建自定义会话，禁用 SSL 验证并设置重试
def create_session():
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.verify = False  # 禁用 SSL 验证
    return session

def load_config():
    """加载 config.json"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config):
    """保存 config.json"""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def get_service_url(service_id, service_data, default_domain):
    """生成服务的完整 URL"""
    domain = service_data.get("domain", default_domain)
    port = service_data.get("port", 80)
    scheme = "https" if port == 443 else "http"
    return f"{scheme}://{domain}:{port}"

def fetch_favicon(service_id, service_data, default_domain, skip_existing=True):
    """抓取单个服务的 favicon"""
    # 检查是否已存在图标文件
    existing_files = list(Path(FAVICON_DIR).glob(f"{service_id}.*"))
    if skip_existing and existing_files:
        print(f"跳过 {service_id}（图标已存在）")
        return existing_files[0].name  # 返回现有文件名

    # 生成服务 URL
    base_url = get_service_url(service_id, service_data, default_domain)
    
    # 常见 favicon 路径
    favicon_paths = [
        "/static/favicon.ico",
        "/images/favicon.ico",
        "/img/favicon.ico",
        "/assets/favicon.ico",
        "/favicon.ico",
        "/favicon.png",
        "/favicon.jpg",
        "/favicon.svg",
    ]

    session = create_session()
    favicon_data = None
    favicon_ext = None

    for path in favicon_paths:
        favicon_url = urljoin(base_url, path)
        try:
            response = session.get(favicon_url, timeout=15)
            if response.status_code == 200:
                # 根据内容类型或URL确定扩展名
                content_type = response.headers.get("Content-Type", "").lower()
                if "image/x-icon" in content_type or favicon_url.endswith(".ico"):
                    favicon_ext = "ico"
                elif "image/png" in content_type or favicon_url.endswith(".png"):
                    favicon_ext = "png"
                elif "image/jpeg" in content_type or favicon_url.endswith((".jpg", ".jpeg")):
                    favicon_ext = "jpg"
                elif "image/svg+xml" in content_type or favicon_url.endswith(".svg"):
                    favicon_ext = "svg"
                else:
                    # 默认使用ico
                    favicon_ext = "ico"
                
                favicon_data = response.content
                break
        except Exception as e:
            print(f"尝试 {favicon_url} 失败: {str(e)[:100]}...")

    if not favicon_data:
        print(f"警告: 无法获取 {service_id} 的 favicon")
        return None

    # 保存文件
    favicon_filename = f"{service_id}.{favicon_ext}"
    favicon_path = os.path.join(FAVICON_DIR, favicon_filename)
    
    with open(favicon_path, "wb") as f:
        f.write(favicon_data)

    # 更新配置
    config = load_config()
    if service_id in config["services"]:
        config["services"][service_id]["favicon"] = favicon_filename
        save_config(config)
    
    print(f"成功保存 {service_id} 的 favicon: {favicon_filename}")
    return favicon_filename

def refresh():
    """刷新所有 favicon（跳过已存在的）"""
    config = load_config()
    default_domain = config["default_domain"]
    services = config["services"]

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for service_id, service_data in services.items():
            futures.append(executor.submit(
                fetch_favicon, 
                service_id, 
                service_data, 
                default_domain, 
                True
            ))
        
        for future in futures:
            future.result()  # 等待所有任务完成

def hard_refresh():
    """强制刷新所有 favicon（先清空）"""
    # 清空目录
    for file in Path(FAVICON_DIR).glob("*"):
        try:
            file.unlink()
        except:
            pass

    # 清空配置中的favicon字段
    config = load_config()
    for service in config["services"].values():
        if "favicon" in service:
            del service["favicon"]
    save_config(config)

    # 执行刷新
    refresh()

if __name__ == "__main__":
    print("=== 开始刷新 favicon ===")
    refresh()