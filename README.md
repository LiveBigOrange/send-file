# 文件快传系统

基于Flask和Socket.IO构建的实时文件传输Web应用，允许用户通过生成的传输码直接进行点对点文件传输。

## 功能特点

- **无需注册**：无需账号即可快速传输文件
- **实时传输**：基于WebSocket技术，支持实时文件传输
- **传输码机制**：通过6位字母数字组合码安全连接发送方和接收方
- **大文件支持**：采用分片传输技术，支持大文件传输
- **断点续传**：支持传输中断后的续传功能
- **简洁界面**：用户友好的界面设计

## 技术栈

- **后端**：Flask, Flask-SocketIO
- **前端**：HTML, JavaScript
- **通信**：WebSocket (Socket.IO)
- **文件处理**：分片传输技术

## 安装与运行

### 环境要求

- Python 3.7+
- pip包管理工具

### 安装步骤

1. 克隆仓库或下载源码

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 启动应用
```bash
python app.py
```

4. 在浏览器中访问 `http://localhost:5000` 开始使用

### 生产环境部署

本应用默认使用Flask开发服务器，不推荐用于生产环境。生产环境部署建议：

```bash
# 使用Gunicorn和eventlet
gunicorn -k eventlet -w 1 app:app
```

或

```bash
# 使用uWSGI
uwsgi --http :5000 --gevent 1000 --http-websockets --master --wsgi-file app.py --callable app
```

## 使用方法

1. **发送文件**：
   - 访问首页或上传页面
   - 点击"创建传输"获取传输码
   - 选择要发送的文件
   - 将传输码分享给接收方

2. **接收文件**：
   - 访问下载页面
   - 输入传输码并连接
   - 等待文件传输完成
   - 下载接收到的文件

## 项目结构

```
send-file/
├── app.py          # 主应用程序
├── requirements.txt # 依赖清单
├── README.md       # 项目说明
├── static/         # 静态资源
├── templates/      # HTML模板
│   ├── index.html  # 首页
│   ├── upload.html # 上传页面
│   └── download.html # 下载页面
└── uploads/        # 文件上传临时目录
```

## 注意事项

- 不推荐在公网环境下使用开发服务器
- 传输过程中请保持页面开启
- 对于大文件传输，建议使用稳定的网络连接 
