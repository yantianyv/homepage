import json
from flask import Flask, render_template, redirect

app = Flask(__name__)

# 读取配置文件
with open('config.json', 'r', encoding='utf-8') as f:
    config_data = json.load(f)

# 获取域名配置
domain = config_data['domain']

# 首页路由，显示动态导航网页
@app.route('/')
def index():
    # 获取配置文件中的跳转项
    return render_template('index.html', services=config_data['services'])

# 动态跳转路由
@app.route('/<service>')
def redirect_to_service(service):
    # 查找配置中的对应服务
    if service in config_data['services']:
        # 获取服务的端口号
        port = config_data['services'][service]['port']
        # 构造完整的 URL
        url = f"{domain}:{port}"
        return redirect(url)
    else:
        return "服务未找到", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

