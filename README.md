# Egg Futures Monitor
鸡蛋期货(JD2609) 监控系统

## 功能特性
- 期货行情自动采集 (AKShare)
- 现货价格采集
- 预警规则配置
- 飞书机器人消息推送
- SQLite 数据存储
- 定时任务调度

## 安装

### 1. 创建并激活 Python 虚拟环境

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

## 配置
复制 `.env.example` 为 `.env` 并填写配置
```bash
cp .env.example .env
```

必填配置项：
- `FEISHU_WEBHOOK_URL`: 飞书群机器人 Webhook 地址

## 运行

**确保虚拟环境已激活**，然后运行：
```bash
python src/main.py
```

### 后台运行（Linux）
```bash
nohup python src/main.py > logs/monitor.log 2>&1 &
```

### 退出虚拟环境
```bash
deactivate
```

## 目录结构
```
egg_monitor/
├── config/              # 配置文件
├── src/
│   ├── collectors/     # 数据采集
│   ├── storage/         # 数据存储
│   ├── analysis/        # 预警分析
│   ├── notification/  # 消息推送
│   ├── scheduler/     # 定时任务
│   └── utils/        # 工具模块
├── data/             # 数据目录
├── logs/             # 日志目录
└── docs/             # 文档
```
