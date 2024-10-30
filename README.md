# MultA: 动态多智能体系统

MultA是一个动态的多智能体系统框架，具有前端和后端服务支持。

## 项目结构
```
src/
├── MultA/
│   ├── __init__.py
│   ├── MultA.py
│   └── types.py
├── backend/
│   ├── __init__.py
│   └── main.py
├── frontend/
│   ├── __init__.py
│   └── app.py
├── run_backend.py
└── run_frontend.py
```

## 安装

1. 克隆仓库：
   ```
   git clone https://github.com/your-repo/MultA.git
   ```

2. 安装依赖：
   ```
   pip install -r requirements.txt
   ```

## 运行

1. 进入src目录：
   ```
   cd src
   ```

2. 启动后端服务：
   ```
   python run_backend.py
   ```

3. 在新的终端窗口中启动前端服务：
   ```
   python run_frontend.py
   ```

4. 在浏览器中打开显示的URL（通常是 http://localhost:8501）来访问MultA聊天界面。

## 使用

在聊天界面中，您可以输入问题并点击"发送"按钮。MultA将处理您的请求并以流式方式返回结果。

## 注意

确保后端服务在前端服务之前启动，以确保WebSocket连接可以正确建立。
写一首与晴天有关的诗要有诗名
我想要生产一款智能网盘的产品，产品经理和市场专员分别有什么看法吗