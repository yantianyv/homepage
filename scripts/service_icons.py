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

        # 查找所有可能的favicon相关链接
        icon_links = soup.find_all("link", rel=lambda x: x and "icon" in x.lower())

        for link in icon_links:
            href = link.get("href")
            if href:
                return urljoin(url, href)

        # 尝试常见路径
        for path in ["/favicon.ico", "/favicon.png", "/img/favicon.svg"]:
            test_url = urljoin(url, path)
            try:
                r = requests.head(test_url, timeout=5)
                if r.status_code == 200:
                    return test_url
            except:
                continue

        return None
    except requests.exceptions.RequestException:
        return None


def download_favicon(domain, service_name, port, output_dir):
    # 创建输出目录（如果不存在）
    os.makedirs(output_dir, exist_ok=True)

    # 获取真正的favicon URL
    favicon_url = get_favicon_url(domain, port)
    if not favicon_url:
        print(f"无法获取 {service_name} 的favicon URL")
        return

    # 输出文件路径
    output_path = os.path.join(output_dir, f"{service_name}.ico")

    try:
        # 发送HTTP请求获取图标
        response = requests.get(favicon_url, timeout=10)
        response.raise_for_status()

        # 保存图标文件
        with open(output_path, "wb") as f:
            f.write(response.content)

    except requests.exceptions.RequestException as e:
        print(f"下载 {service_name} 的图标失败: {e}")


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

    # 为每个服务下载图标
    for service_key, service_info in services.items():
        service_name = service_info.get("name", service_key)
        port = service_info.get("port")
        service_domain = service_info.get("domain", default_domain)

        if not port:
            print(f"服务 {service_name} 缺少端口配置，跳过")
            continue

        download_favicon(service_domain, service_name, port, output_dir)


if __name__ == "__main__":
    refresh()
