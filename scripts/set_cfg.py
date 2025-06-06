#!/usr/bin/env python3

import json
import os
import platform
from scripts import get_favicon

# 配置文件路径
CONFIG_FILE = "config.json"


# 清屏函数，支持不同操作系统
def clear():
    system_name = platform.system()
    if system_name == "Windows":
        os.system("cls")  # Windows系统使用cls
    else:
        os.system("clear")  # 类Unix系统使用clear


# 读取配置文件
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return {
            "default_domain": "127.0.0.1",
            "site_title": "请使用启动参数 -s 设置域名和标题",
            "services": {},
        }


# 保存配置文件（按服务ID排序）
def save_config(config):
    # 对services字典按键排序
    sorted_services = dict(sorted(config["services"].items()))
    config["services"] = sorted_services
    
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


# 打印分隔线
def print_line(char="-", length=50):
    print(char * length)


# 打印标题
def print_title(title):
    print_line("=")
    print(f"{title:^50}")
    print_line("=")


# 显示服务列表，按服务ID排序
def show_services(config):
    clear()  # 清屏
    print_title("当前配置的服务")
    services = sorted(config["services"].items())  # 按服务ID排序
    if not services:
        print("没有配置任何服务！")
    else:
        for service_id, details in services:
            domain = details.get("domain", config["default_domain"])
            print(f"- {service_id}: {details['name']} (端口: {details['port']}, 域名: {domain})")
    input("\n按回车返回主菜单...")


# 添加服务（整合了域名设置）
def add_service(config):
    clear()  # 清屏
    print_title("添加服务")
    service_id = input("请输入服务ID: ")
    display_name = input("请输入显示名称: ")

    while True:
        try:
            port = int(input("请输入端口号: "))
            break
        except ValueError:
            print("端口号必须是数字，请重新输入。")

    domain = input("请输入域名 (留空使用全局域名): ").strip()

    if service_id in config["services"]:
        print(f"服务 {service_id} 已存在！")
    else:
        service_data = {"name": display_name, "port": port}
        if domain:  # 只有输入了域名才添加到服务配置中
            service_data["domain"] = domain

        config["services"][service_id] = service_data
        save_config(config)

        # 显示最终使用的域名
        final_domain = domain if domain else config["default_domain"]
        print(f"服务 {service_id} 添加成功！将使用域名: {final_domain}")
    input("\n按回车返回主菜单...")


# 删除服务
def delete_service(config):
    clear()  # 清屏
    services = list(config["services"].keys())
    if not services:
        print("没有配置任何服务，无法删除！")
        input("\n按回车返回主菜单...")
        return

    print_title("删除服务")
    print("请选择要删除的服务 (输入 0 取消操作)：")
    for i, service_id in enumerate(services, start=1):
        print(f"{i}. {service_id}")

    while True:
        try:
            choice = int(input("\n请输入服务编号: "))
            if choice == 0:
                print("取消删除操作。")
                return
            elif 1 <= choice <= len(services):
                break
            else:
                print("无效的选择，请重新输入。")
        except ValueError:
            print("请输入有效的数字。")

    service_id = services[choice - 1]
    del config["services"][service_id]
    save_config(config)
    print(f"服务 {service_id} 删除成功！")
    input("\n按回车返回主菜单...")


# 设置全局域名
def set_default_domain(config):
    clear()  # 清屏
    print_title("设置全局域名")
    domain = input(f"当前全局域名: {config['default_domain']}\n请输入新的全局域名 (按回车保持当前域名): ")
    if domain:
        config["default_domain"] = domain
        save_config(config)
        print(f"全局域名已设置为 {domain}")
    else:
        print("全局域名未修改。")
    input("\n按回车返回主菜单...")


# 设置标题
def set_title(config):
    clear()  # 清屏
    print_title("设置标题")
    site_title = input(f"当前标题: {config['site_title']}\n请输入新的标题 (按回车保持当前标题): ")
    if site_title:
        config["site_title"] = site_title
        save_config(config)
        print(f"标题已设置为 {site_title}")
    else:
        print("标题未修改。")
    input("\n按回车返回主菜单...")


# 主菜单（简化了选项）
def main_menu():
    config = load_config()

    while True:
        clear()  # 清屏
        print_title("配置管理系统")
        print("1. 查看服务")
        print("2. 添加服务")
        print("3. 删除服务")
        print("4. 设置全局域名")
        print("5. 设置标题")
        print("6. 退出")

        choice = input("\n请输入操作编号 (1-6): ")

        if choice == "1":
            show_services(config)
        elif choice == "2":
            add_service(config)
        elif choice == "3":
            delete_service(config)
        elif choice == "4":
            set_default_domain(config)
        elif choice == "5":
            set_title(config)
        elif choice == "6":
            get_favicon.clear_favicons()
            print("感谢使用配置管理系统，配置通常会在1分钟内或下次启动时生效，再见！")
            break
        else:
            print("无效的选择，请重新输入。")


if __name__ == "__main__":
    main_menu()

