import os
import requests
from urllib.parse import urljoin
import json
from bs4 import BeautifulSoup


def get_favicon_url(domain, port):
    url = f"http://{domain}:{port}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # 查找可能的favicon链接
        icon_link = soup.find("link", rel=lambda x: x and x.lower() in ["icon", "shortcut icon"])

        if icon_link and icon_link.get("href"):
            favicon_url = urljoin(url, icon_link["href"])
            return favicon_url

        # 如果没有找到，尝试默认的favicon.ico
        return urljoin(url, "favicon.ico")
    except requests.exceptions.RequestException as e:
        # print(f"获取 {url} 的favicon链接失败: {e}")
        return None


def download_favicon(domain, service_name, port, output_dir):
    # 创建输出目录（如果不存在）
    os.makedirs(output_dir, exist_ok=True)

    # 获取真正的favicon URL
    favicon_url = get_favicon_url(domain, port)
    if not favicon_url:
        print(f"无法获取 {service_name} 的favicon URL")
        return None

    try:
        # 发送HTTP请求获取图标
        response = requests.get(favicon_url, timeout=10)
        response.raise_for_status()

        # 根据Content-Type确定文件扩展名
        content_type = response.headers.get("Content-Type", "").lower()
        if "png" in content_type:
            ext = ".png"
        elif "jpeg" in content_type or "jpg" in content_type:
            ext = ".jpg"
        elif "svg" in content_type:
            ext = ".svg"
        elif "x-icon" in content_type or "vnd.microsoft.icon" in content_type:
            ext = ".ico"
        else:
            # 默认使用URL中的扩展名，如果没有则使用.ico
            ext = os.path.splitext(favicon_url)[1] or ".ico"

        filename = f"{service_name}{ext}"
        output_path = os.path.join(output_dir, filename)

        # 保存图标文件
        with open(output_path, "wb") as f:
            f.write(response.content)

        return {"url": favicon_url, "local_path": f"/static/icons/{filename}", "filename": filename}

    except requests.exceptions.RequestException as e:
        print(f"下载 {service_name} 的图标失败: {e}")
        return None


def refresh():
    # 读取配置文件
    config_path = "config.json"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        print(f"读取配置文件失败: {e}")
        return

    default_domain = config.get("default_domain", "127.0.0.1")
    services = config.get("services", {})

    if not services:
        print("配置文件中没有服务配置")
        return

    # 输出目录
    output_dir = "./static/icons"

    # 记录是否有配置变更
    config_changed = False

    # 为每个服务下载图标
    for service_key, service_info in services.items():
        service_name = service_info.get("name", service_key)
        port = service_info.get("port")
        service_domain = service_info.get("domain", default_domain)

        if not port:
            print(f"服务 {service_name} 缺少端口配置，跳过")
            continue

        result = download_favicon(service_domain, service_name, port, output_dir)
        if result:
            # 如果配置中没有图标信息，或者URL有变化，则更新配置
            if "icon" not in service_info or service_info["icon"].get("url") != result["url"]:
                service_info["icon"] = {"url": result["url"], "path": result["local_path"], "filename": result["filename"]}
                config_changed = True

    # 如果配置有变更，则保存
    if config_changed:
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            print("配置文件已更新")
        except Exception as e:
            print(f"保存配置文件失败: {e}")


if __name__ == "__main__":
    refresh()
