import json
import os
import requests
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# 配置路径
CONFIG_PATH = "config.json"
FAVICON_DIR = "favicons"  # 输出目录改为 favicons

# 确保 favicons 目录存在
os.makedirs(FAVICON_DIR, exist_ok=True)

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
    return f"http://{domain}:{port}"

def fetch_favicon(service_id, service_data, default_domain, skip_existing=True):
    """抓取单个服务的 favicon"""
    # 检查是否已存在图标文件（仅通过文件存在性判断）
    existing_files = list(Path(FAVICON_DIR).glob(f"{service_id}.*"))
    if skip_existing and existing_files:
        print(f"跳过 {service_id}（图标已存在）")
        return

    # 生成服务 URL
    url = get_service_url(service_id, service_data, default_domain)

    # 尝试从常见路径获取 favicon
    favicon_urls = [
        urljoin(url, "/favicon.ico"),
        urljoin(url, "/favicon.png"),
        urljoin(url, "/favicon.jpg"),
    ]

    # 尝试抓取
    favicon_data = None
    favicon_ext = None
    for favicon_url in favicon_urls:
        try:
            response = requests.get(favicon_url, timeout=5)
            if response.status_code == 200:
                content_type = response.headers.get("Content-Type", "")
                if "image/x-icon" in content_type:
                    favicon_ext = "ico"
                elif "image/png" in content_type:
                    favicon_ext = "png"
                elif "image/jpeg" in content_type:
                    favicon_ext = "jpg"
                else:
                    # 根据 URL 猜测扩展名
                    favicon_ext = favicon_url.split(".")[-1].lower()
                    if favicon_ext not in ["ico", "png", "jpg", "jpeg"]:
                        favicon_ext = "ico"  # 默认
                favicon_data = response.content
                break
        except Exception as e:
            print(f"抓取 {service_id} 的 favicon 失败（{favicon_url}）: {e}")

    if not favicon_data:
        print(f"无法获取 {service_id} 的 favicon")
        return

    # 保存 favicon 文件
    favicon_filename = f"{service_id}.{favicon_ext}"
    favicon_path = os.path.join(FAVICON_DIR, favicon_filename)

    with open(favicon_path, "wb") as f:
        f.write(favicon_data)

    # 更新 config.json 的 favicon 字段
    config = load_config()
    config["services"][service_id]["favicon"] = favicon_filename
    save_config(config)
    print(f"已保存 {service_id} 的 favicon: {favicon_filename}")

def refresh():
    """刷新所有 favicon（跳过已存在的）"""
    config = load_config()
    default_domain = config["default_domain"]
    services = config["services"]

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(fetch_favicon, service_id, service_data, default_domain, True)
            for service_id, service_data in services.items()
        ]
        for future in futures:
            future.result()  # 等待所有任务完成

def hard_refresh():
    """强制刷新所有 favicon（先清空）"""
    # 清空 favicons 目录
    for file in Path(FAVICON_DIR).glob("*"):
        file.unlink()

    # 清空 config 中所有 favicon 字段
    config = load_config()
    for service_id in config["services"]:
        config["services"][service_id].pop("favicon", None)
    save_config(config)

    # 执行普通刷新
    refresh()

if __name__ == "__main__":
    # 示例调用
    print("=== 刷新 favicon（跳过已存在的）===")
    refresh()

    print("\n=== 强制刷新 favicon（清空后重新抓取）===")
    hard_refresh()