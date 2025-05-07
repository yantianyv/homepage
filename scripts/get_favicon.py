import os
import requests
from urllib.parse import urljoin
import json
from bs4 import BeautifulSoup
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# 禁用SSL警告（仅限开发环境）
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# 通用请求头
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8'
}

def get_favicon_url(domain, port):
    """获取网站favicon的URL"""
    # 处理默认端口
    if port == 80:
        base_url = f"http://{domain}"
    elif port == 443:
        base_url = f"https://{domain}"
    else:
        base_url = f"http://{domain}:{port}"

    try:
        # 尝试HTTPS优先
        if not base_url.startswith("https://"):
            https_url = f"https://{domain}:{port}" if port != 80 else f"https://{domain}"
            try:
                requests.get(https_url, headers=DEFAULT_HEADERS, timeout=5, verify=False)
                base_url = https_url
            except:
                pass

        # 获取首页内容
        response = requests.get(base_url, headers=DEFAULT_HEADERS, timeout=10, verify=False)
        soup = BeautifulSoup(response.text, "html.parser")

        # 查找所有可能的favicon链接
        icon_links = soup.find_all("link", rel=lambda x: x and x.lower() in ["icon", "shortcut icon"])
        for link in icon_links:
            if link.get("href"):
                favicon_url = urljoin(base_url, link["href"])
                # 验证链接是否有效
                if requests.head(favicon_url, headers=DEFAULT_HEADERS, timeout=5, verify=False).status_code == 200:
                    return favicon_url

        # 尝试常见路径
        common_paths = ["/favicon.ico", "/static/favicon.ico", "/img/favicon.ico", "/assets/favicon.ico"]
        for path in common_paths:
            favicon_url = urljoin(base_url, path)
            if requests.head(favicon_url, headers=DEFAULT_HEADERS, timeout=5, verify=False).status_code == 200:
                return favicon_url

        # 最后尝试默认favicon.ico
        default_favicon = urljoin(base_url, "favicon.ico")
        if requests.head(default_favicon, headers=DEFAULT_HEADERS, timeout=5, verify=False).status_code == 200:
            return default_favicon

        return None

    except Exception as e:
        print(f"获取 {domain} 的favicon URL失败: {str(e)}")
        return None

def download_favicon(domain, service_name, port, output_dir):
    """下载并保存favicon"""
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取favicon URL
    favicon_url = get_favicon_url(domain, port)
    if not favicon_url:
        print(f"无法获取 {service_name} 的favicon URL")
        return None

    try:
        # 下载favicon
        response = requests.get(
            favicon_url,
            headers=DEFAULT_HEADERS,
            timeout=15,
            verify=False,
            stream=True
        )
        response.raise_for_status()

        # 确定文件扩展名
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
            # 从URL获取扩展名或默认使用.ico
            ext = os.path.splitext(favicon_url)[1] or ".ico"

        # 清理服务名称用于文件名
        safe_name = "".join(c for c in service_name if c.isalnum() or c in (' ', '_')).rstrip()
        filename = f"{safe_name}{ext}"
        output_path = os.path.join(output_dir, filename)

        # 保存文件
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)

        return {
            "url": response.url,  # 注意使用最终URL（处理重定向后）
            "local_path": f"/static/icons/{filename}",
            "filename": filename
        }

    except Exception as e:
        print(f"下载 {service_name} 的图标失败: {str(e)}")
        return None

def refresh():
    """刷新所有服务的favicon"""
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
    output_dir = "./icons"
    config_changed = False

    # 为每个服务下载图标
    for service_key, service_info in services.items():
        service_name = service_info.get("name", service_key)
        port = service_info.get("port")
        service_domain = service_info.get("domain", default_domain)

        if not port:
            print(f"服务 {service_name} 缺少端口配置，跳过")
            continue

        print(f"正在处理: {service_name}...")
        result = download_favicon(service_domain, service_name, port, output_dir)
        
        if result:
            # 检查是否需要更新配置
            current_icon = service_info.get("icon", {})
            if (not current_icon or 
                current_icon.get("url") != result["url"] or
                current_icon.get("filename") != result["filename"]):
                
                service_info["icon"] = {
                    "url": result["url"],
                    "path": result["local_path"],
                    "filename": result["filename"]
                }
                config_changed = True
                print(f"已更新 {service_name} 的图标")
            else:
                print(f"{service_name} 的图标无需更新")
        else:
            print(f"{service_name} 的图标获取失败")

    # 保存配置变更
    if config_changed:
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            print("配置文件已更新")
        except Exception as e:
            print(f"保存配置文件失败: {e}")

if __name__ == "__main__":
    refresh()