# 鸡蛋期货监测系统 - 实施计划

## 用户确认的技术选型
- 消息推送：**飞书群机器人**
- 数据库：**仅SQLite**
- 部署：**直接Python运行，暂不使用Docker**
- 安全要求：**不暴露公网API，仅本地/内网访问**

---

## 一、调整后的目录结构

```
egg_monitor/
├── .gitignore
├── LICENSE
├── README.md
├── requirements.txt            # Python依赖
├── .env.example                # 环境变量示例
├── config/                     # 配置文件
│   ├── __init__.py
│   ├── settings.py             # 系统配置
│   └── alert_rules.yaml        # 预警规则配置
├── src/                        # 源代码
│   ├── __init__.py
│   ├── main.py                 # FastAPI入口(仅本地访问)
│   ├── collectors/             # 数据采集模块
│   │   ├── __init__.py
│   │   ├── futures_collector.py    # 期货数据采集(TqSdk/AKShare)
│   │   └── spot_collector.py       # 现货价格采集(爬虫)
│   ├── storage/                # 数据存储模块
│   │   ├── __init__.py
│   │   ├── database.py         # SQLite数据库连接
│   │   ├── models.py           # SQLAlchemy ORM模型
│   │   └── crud.py             # 数据库操作
│   ├── analysis/               # 预警分析模块
│   │   ├── __init__.py
│   │   ├── rule_engine.py      # 规则引擎
│   │   └── indicators.py       # 指标计算
│   ├── notification/           # 消息推送模块
│   │   ├── __init__.py
│   │   ├── notifier.py         # 统一通知接口
│   │   └── feishu.py           # 飞书推送(移除微信)
│   ├── scheduler/              # 定时任务模块
│   │   ├── __init__.py
│   │   └── jobs.py             # 定时任务定义
│   └── utils/                  # 工具模块
│       ├── __init__.py
│       └── logger.py           # 日志工具
├── data/                       # 数据目录
│   ├── db/                     # SQLite数据库文件
│   ├── uploads/                # 人工上传文件目录
│   └── backup/                 # 数据备份目录
├── logs/                       # 日志目录
└── docs/                       # 文档
    ├── plan.md
    └── architecture.md
```

---

## 二、实施步骤

### Phase 1: 项目初始化 (1-2小时)
1. 创建目录结构
2. 编写 requirements.txt
3. 配置环境变量模板
4. 配置 .gitignore

### Phase 2: 基础模块开发 (4-6小时)
1. 配置模块 (config/settings.py)
2. 日志工具 (src/utils/logger.py)
3. 数据库连接 (src/storage/database.py)
4. ORM模型定义 (src/storage/models.py)
5. 数据库CRUD封装 (src/storage/crud.py)

### Phase 3: 数据采集模块 (4-6小时)
1. 期货数据采集器 (TqSdk/AKShare)
2. 现货价格采集器 (生意社爬虫)

### Phase 4: 预警分析模块 (2-3小时)
1. 指标计算模块
2. 规则引擎
3. 预警规则配置文件

### Phase 5: 消息推送模块 (1-2小时)
1. 飞书机器人推送
2. 统一通知接口

### Phase 6: 定时任务模块 (1-2小时)
1. APScheduler定时任务配置
2. 数据采集、预警检查、备份任务

### Phase 7: 系统测试 (2-3小时)
1. 数据采集测试
2. 数据库读写测试
3. 预警规则测试
4. 消息推送测试

---

## 三、安全措施
- API绑定 127.0.0.1，不监听公网
- 使用 .env 文件存储敏感信息(飞书Webhook、TqSdk账号等)
- .env 文件加入 .gitignore
- 所有外部请求添加 User-Agent 和请求间隔限制
- 数据库文件定期备份

---

## 四、待开发文件清单
1. requirements.txt
2. .env.example
3. config/settings.py
4. config/alert_rules.yaml
5. src/utils/logger.py
6. src/storage/database.py
7. src/storage/models.py
8. src/storage/crud.py
9. src/collectors/futures_collector.py
10. src/collectors/spot_collector.py
11. src/analysis/indicators.py
12. src/analysis/rule_engine.py
13. src/notification/feishu.py
14. src/notification/notifier.py
15. src/scheduler/jobs.py
16. src/main.py
