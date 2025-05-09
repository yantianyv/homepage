import os
import shutil
import requests
from urllib.parse import urljoin
import json
from bs4 import BeautifulSoup
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import threading
from queue import Queue
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# 禁用SSL警告（仅限开发环境）
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# 通用请求头
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8'
}

# 全局变量
config = None
config_lock = threading.Lock()
output_dir = "./favicons"
config_changed = False

def try_get_favicon(base_url, domain, port):
    """尝试从单个base_url获取favicon"""
    try:
        # 获取首页解析HTML
        response = requests.get(base_url, headers=DEFAULT_HEADERS, timeout=10, verify=False)
        soup = BeautifulSoup(response.text, "html.parser")

        # 尝试常见路径
        common_paths = ["/static/favicon.ico", "/img/favicon.ico", "/assets/favicon.ico", "favicon.ico"]
        for path in common_paths:
            favicon_url = urljoin(base_url, path)
            try:
                response = requests.head(favicon_url, headers=DEFAULT_HEADERS, timeout=10, verify=False)
                if response.status_code == 200 and 'image/' in response.headers.get('Content-Type', '').lower():
                    content_type = response.headers.get('Content-Type')
                    if 'image' in content_type:
                        return favicon_url
            except:
                continue

        # 查找所有可能的favicon链接
        icon_links = soup.find_all("link", rel=lambda x: x and x.lower() in ["icon", "shortcut icon"])
        for link in icon_links:
            if link.get("href"):
                favicon_url = urljoin(base_url, link["href"])
                try:
                    if requests.head(favicon_url, headers=DEFAULT_HEADERS, timeout=10, verify=False).status_code == 200:
                        return favicon_url
                except:
                    continue
    except:
        return None
    return None

def get_favicon_url(domain, port):
    """获取网站favicon的URL（多线程改进版）"""
    # 处理默认端口
    schemes = ['http', 'https'] 
    base_urls = []
    
    if port == 80:
        base_urls.append(f"http://{domain}")
    elif port == 443:
        base_urls.append(f"https://{domain}")
    else:
        for scheme in schemes:
            base_urls.append(f"{scheme}://{domain}:{port}")

    # 使用线程池并行尝试所有base_urls
    with ThreadPoolExecutor(max_workers=32) as executor:
        futures = []
        for base_url in base_urls:
            # 对每个base_url发起10次并行尝试
            for _ in range(10):
                futures.append(executor.submit(try_get_favicon, base_url, domain, port))
                time.sleep(5)
        
        # 获取第一个成功的结果
        for future in as_completed(futures):
            result = future.result()
            if result is not None:
                # 取消其他未完成的任务
                for f in futures:
                    f.cancel()
                return result
    return None

def download_favicon(service_key, service_info, default_domain):
    """下载并保存favicon"""
    global config_changed
    
    service_name = service_info.get("name", service_key)
    port = service_info.get("port")
    service_domain = service_info.get("domain", default_domain)

    if not port:
        print(f"服务 {service_key} 缺少端口配置，跳过")
        return

    # 检查是否已有favicon且文件存在
    current_favicon = service_info.get("favicon")
    if current_favicon and os.path.exists(os.path.join(output_dir, current_favicon)):
        return
    else:
        print(f"开始抓取服务 {service_key} 的图标")
    
    # 获取favicon URL
    favicon_url = get_favicon_url(service_domain, port)
    if not favicon_url:
        print(f"无法获取服务 {service_key} 的favicon URL")
        return
    else:
        print(f"正在从 {favicon_url} 抓取图标")

    try:
        # 下载favicon
        response = requests.get(
            favicon_url,
            headers=DEFAULT_HEADERS,
            timeout=10,
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

        # 使用服务ID作为文件名
        filename = f"{service_key}{ext}"
        output_path = os.path.join(output_dir, filename)

        # 保存文件
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)

        # 检查是否需要更新配置
        if not current_favicon or current_favicon != filename:
            with config_lock:
                service_info["favicon"] = filename
                config_changed = True
                print(f"已更新服务 {service_key} 的图标配置为 {filename}")

    except Exception as e:
        print(f"下载服务 {service_key} 的图标失败: {str(e)}")

def clear_favicons():
    """清空图标目录"""
    global config_changed
    
    if os.path.exists(output_dir):
        # 删除目录中的所有文件
        for filename in os.listdir(output_dir):
            file_path = os.path.join(output_dir, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"删除 {file_path} 失败: {e}")
        
        print("已清空图标目录")
        
        # 重置所有服务的favicon配置
        with config_lock:
            if config is not None:
                for service_info in config.get("services", {}).values():
                    if "favicon" in service_info:
                        del service_info["favicon"]
                        config_changed = True
    else:
        print("图标目录不存在，无需清空")

def worker(task_queue, default_domain):
    """工作线程函数"""
    while not task_queue.empty():
        service_key, service_info = task_queue.get()
        try:
            download_favicon(service_key, service_info, default_domain)
        finally:
            task_queue.task_done()

def refresh():
    """刷新所有服务的favicon"""
    global config, config_changed
    
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

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 创建任务队列
    task_queue = Queue()
    for service_key, service_info in services.items():
        task_queue.put((service_key, service_info))

    # 创建工作线程
    thread_count = min(8, len(services))  # 最多32个线程
    threads = []
    for i in range(thread_count):
        t = threading.Thread(target=worker, args=(task_queue, default_domain))
        t.start()
        threads.append(t)

    # 等待所有任务完成
    task_queue.join()

    # 保存配置变更
    if config_changed:
        try:
            with config_lock:  # 虽然所有线程已完成，但加锁更安全
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
            print("配置文件已更新")
        except Exception as e:
            print(f"保存配置文件失败: {e}")

def hard_refresh():
    """先清空图标再刷新"""
    # 读取配置文件（确保config已加载）
    global config
    if config is None:
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            print(f"读取配置文件失败: {e}")
            return
    
    # 清空图标
    clear_favicons()
    
    # 刷新图标
    refresh()

if __name__ == "__main__":
    hard_refresh()