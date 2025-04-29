import os
import requests
from urllib.parse import urljoin
import json
from bs4 import BeautifulSoup
from PIL import Image
import io


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


def convert_to_ico(image_data):
    """将图像数据转换为ICO格式"""
    try:
        # 从字节数据打开图像
        img = Image.open(io.BytesIO(image_data))

        # 如果图像有透明度通道，确保保留它
        if img.mode in ("RGBA", "LA"):
            # 创建一个新的透明背景图像
            ico_img = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ico_img.paste(img, (0, 0), img)
        else:
            ico_img = img.convert("RGB")

        # 将图像保存为ICO格式到内存中
        ico_bytes = io.BytesIO()
        ico_img.save(ico_bytes, format="ICO", sizes=[(ico_img.size[0], ico_img.size[1])])
        return ico_bytes.getvalue()
    except Exception as e:
        print(f"图像转换失败: {e}")
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

        # 获取内容类型和文件扩展名
        content_type = response.headers.get("Content-Type", "").lower()
        file_ext = os.path.splitext(favicon_url)[1].lower()

        # 检查是否是ICO格式
        is_ico = (".ico" in file_ext) or ("image/x-icon" in content_type)

        if is_ico:
            # 直接保存ICO文件
            with open(output_path, "wb") as f:
                f.write(response.content)
        else:
            # 转换为ICO格式
            ico_data = convert_to_ico(response.content)
            if ico_data:
                with open(output_path, "wb") as f:
                    f.write(ico_data)
                print(f"已转换并保存 {service_name} 的ICO图标")
            else:
                print(f"无法转换 {service_name} 的图标为ICO格式")

    except requests.exceptions.RequestException as e:
        print(f"下载 {service_name} 的图标失败: {e}")
    except Exception as e:
        print(f"处理 {service_name} 的图标时出错: {e}")


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
