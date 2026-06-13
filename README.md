# Egg Futures Monitor
鸡蛋期货(JD2609) 监控系统

## 功能特性

### 核心功能
- ✅ 期货行情自动采集 (AKShare + 大商所API)
- ✅ 现货价格采集（鸡蛋、玉米、豆粕）
- ✅ 仓单数据采集（大商所仓单日报）
- ✅ 持仓数据采集（大商所前20持仓）
- ✅ 预警规则配置（价格、持仓、仓单激增）
- ✅ 飞书机器人消息推送

### 新增功能（v2.0）
- ✅ **产业数据CSV上传**：支持存栏、鸡苗、淘汰鸡、冷库库存等数据录入
- ✅ **每日数据汇总推送**：交易日下午4:30推送完整数据汇总
- ✅ **黑天鹅关键词监测**：监测禽流感、抛储、灾害天气等风险
- ✅ **数据自动备份**：每周日自动备份，保留最近4周

### 数据存储
- SQLite 数据库（6张表）
- 自动备份机制
- 数据去重与完整性检查

### 定时任务调度
- 交易日行情采集（盘前+盘后）
- 每日现货价格采集
- 每日仓单数据采集
- 每周五持仓数据采集
- 每日黑天鹅监测
- 每周日数据备份

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

### 测试接口（手动刷新数据）

**刷新所有监测数据并发送推送**:
```bash
python scripts/test_refresh_and_push.py
```

此脚本会执行：
1. 采集期货行情（JD2609）
2. 采集现货价格（鸡蛋、玉米、豆粕）
3. 采集仓单数据（大商所）
4. 运行预警检查
5. 发送每日汇总推送到飞书

**单独测试模块**:
```bash
# 测试产业数据上传
python -m src.utils.industrial_uploader data/uploads/industrial_sample.csv

# 测试每日汇总推送
python -m src.notification.daily_summary

# 测试黑天鹅监测
python -m src.utils.black_swan_monitor

# 测试数据备份
python -m src.utils.backup
```

### 后台运行（Linux）
```bash
cd /home/app/egg_monitor
git pull
sudo systemctl restart egg-monitor
```

```
# 查看服务状态（应该显示active (running)）
systemctl status egg-monitor

# 实时查看日志（按Ctrl+C退出）
journalctl -u egg-monitor -f

# 查看今天的所有日志
journalctl -u egg-monitor --since today
```

### 退出虚拟环境
```bash
deactivate
```

## 目录结构
```
egg_monitor/
├── config/              # 配置文件
│   ├── settings.py      # 系统配置
│   └── alert_rules.yaml # 预警规则
├── src/
│   ├── collectors/      # 数据采集
│   │   ├── futures_collector.py       # 期货行情
│   │   ├── spot_collector.py          # 现货价格
│   │   ├── futures_receipt_collector.py # 仓单数据
│   │   ├── futures_holding_collector.py # 持仓数据
│   │   └── dce_client.py              # 大商所API客户端
│   ├── storage/         # 数据存储
│   │   ├── database.py  # 数据库连接
│   │   ├── models.py    # ORM模型（6张表）
│   │   └── crud.py      # 数据库操作
│   ├── analysis/        # 预警分析
│   │   ├── rule_engine.py # 预警规则引擎
│   │   └ indicators.py   # 指标计算（基差等）
│   ├── notification/    # 消息推送
│   │   ├── notifier.py    # 统一通知分发
│   │   ├── feishu.py      # 飞书机器人推送
│   │   └ daily_report.py  # 每日报告
│   │   └ daily_summary.py # 每日汇总（v2.0）
│   ├── scheduler/       # 定时任务
│   │   └ jobs.py        # 定时任务定义
│   └ utils/             # 工具模块
│   │   ├── industrial_uploader.py # 产业数据上传（v2.0）
│   │   ├── black_swan_monitor.py # 黑天鹅监测（v2.0）
│   │   ├── backup.py             # 数据备份（v2.0）
│   │   └ logger.py               # 日志工具
│   └ main.py            # 程序入口
├── scripts/             # 脚本工具
│   ├── init_database.py           # 数据库初始化
│   └ test_refresh_and_push.py     # 测试刷新接口（v2.0）
├── data/
│   ├── db/              # SQLite 数据库文件
│   ├── uploads/         # 人工上传目录（产业数据CSV）
│   └ backup/            # 备份目录
├── logs/                # 运行日志
├── docs/                # 文档
│   ├── plan.md          # 业务规划
│   ├── dev_spec.md      # 技术规格
│   ├── development_summary.md # 开发总结（v2.0）
│   ├── quick_start.md   # 快速使用指南（v2.0）
│   └ dce_receipt_issue.md # 大商所仓单API问题分析
├── test_feishu.py       # 飞书连接测试
├── requirements.txt     # Python 依赖
├── .env.example         # 环境变量示例
└ README.md              # 本文档
```

## 数据库表结构

系统包含6张核心数据表：

| 表名 | 说明 | 主要字段 |
|------|------|----------|
| `futures_quote` | 期货行情 | symbol, datetime, open, close, volume, open_interest |
| `futures_receipt` | 仓单数据 | date, symbol, receipt_qty, change, warehouse |
| `futures_holding` | 持仓数据 | date, symbol, long_qty, short_qty, long_change |
| `spot_price` | 现货价格 | date, category, region, price, unit, source |
| `industrial_inventory` | 产业数据 | date, category, inventory, mom, yoy, source |
| `alert_record` | 预警记录 | level, title, content, rule_id, status |

## 定时任务时间表

| 时间 | 任务 | 说明 |
|------|------|------|
| 每日 09:00 | 黑天鹅监测 | 检查禽流感、抛储等关键词 |
| 每日 09:30 | 期货行情采集 | 盘前行情 + 预警检查 |
| 每日 10:00 | 现货价格采集 | 鸡蛋、玉米、豆粕价格 |
| 每日 15:40 | 期货行情采集 | 盘后行情 + 预警检查 |
| 每日 16:00 | 每日报告 | 简要推送 |
| 每日 16:30 | 每日汇总 | 详细汇总推送（v2.0） |
| 每日 16:30 | 仓单数据采集 | 大商所仓单日报 |
| 每周五 17:00 | 持仓数据采集 | 大商所前20持仓 |
| 每周日 00:00 | 数据备份 | 备份数据库和日志（v2.0） |

## 版本历史

- **v1.0** (2026-06-13): 初始版本，完成基础框架搭建
- **v2.0** (2026-06-14): 新增产业数据上传、每日汇总、黑天鹅监测、数据备份

## 相关文档

- [docs/quick_start.md](docs/quick_start.md) - 快速使用指南
- [docs/development_summary.md](docs/development_summary.md) - 开发总结
- [docs/dev_spec.md](docs/dev_spec.md) - 技术规格文档
- [docs/plan.md](docs/plan.md) - 业务规划文档
