
# 鸡蛋期货(JD2609)监测系统 - 后端架构设计

## 一、系统概述

### 1.1 系统目标
为鸡蛋期货JD2609提供全维度监测，涵盖期货行情、现货价格、产业数据，实现数据采集、存储、预警分析、消息推送的自动化闭环。

### 1.2 设计原则
- **简洁可扩展**：避免过度设计，模块化便于后续扩展
- **低成本优先**：优先使用免费数据源，SQLite起步
- **稳定可靠**：完善的日志和健康检查机制
- **部署友好**：适配腾讯云Linux服务器

---

## 二、技术选型

| 层次 | 技术选型 | 说明 |
|------|----------|------|
| **开发语言** | Python 3.10+ | 生态丰富，数据处理能力强 |
| **Web框架** | FastAPI | 高性能、异步支持、自动生成API文档 |
| **数据采集** | TqSdk / AKShare / requests + BeautifulSoup | 多源数据适配 |
| **数据存储** | SQLite (初期) / MySQL (后期扩展) | 轻量起步，按需升级 |
| **定时任务** | APScheduler | 灵活的定时调度 |
| **消息推送** | 企业微信群机器人 / 飞书群机器人 | Webhook方式，易接入 |
| **日志** | loguru | 结构化日志，便于排查问题 |
| **部署** | Docker + docker-compose | 环境隔离，易于迁移 |

---

## 三、目录结构

```
egg_monitor/
├── .gitignore
├── LICENSE
├── README.md
├── docker-compose.yml          # Docker编排配置
├── requirements.txt            # Python依赖
├── .env.example                # 环境变量示例
├── config/                     # 配置文件
│   ├── __init__.py
│   ├── settings.py             # 系统配置
│   ├── alert_rules.yaml        # 预警规则配置
│   └── sources.yaml            # 数据源配置
├── src/                        # 源代码
│   ├── __init__.py
│   ├── main.py                 # FastAPI入口
│   ├── collectors/             # 数据采集模块
│   │   ├── __init__.py
│   │   ├── futures_collector.py    # 期货数据采集(TqSdk/大商所)
│   │   ├── spot_collector.py       # 现货价格采集(爬虫)
│   │   └── industrial_collector.py # 产业数据采集(人工录入接口)
│   ├── storage/                # 数据存储模块
│   │   ├── __init__.py
│   │   ├── database.py         # 数据库连接管理
│   │   ├── models.py           # ORM模型定义
│   │   └── crud.py             # 数据库操作
│   ├── analysis/               # 预警分析模块
│   │   ├── __init__.py
│   │   ├── rule_engine.py      # 规则引擎
│   │   └── indicators.py       # 指标计算
│   ├── notification/           # 消息推送模块
│   │   ├── __init__.py
│   │   ├── notifier.py         # 统一通知接口
│   │   ├── wechat.py           # 企业微信推送
│   │   └── feishu.py           # 飞书推送
│   ├── scheduler/              # 定时任务模块
│   │   ├── __init__.py
│   │   └── jobs.py             # 定时任务定义
│   ├── api/                    # API接口模块
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── futures.py      # 期货数据接口
│   │   │   ├── spot.py         # 现货数据接口
│   │   │   ├── industrial.py   # 产业数据接口
│   │   │   ├── alert.py        # 预警数据接口
│   │   │   └── system.py       # 系统管理接口
│   │   └── schemas.py          # Pydantic模型定义
│   └── utils/                  # 工具模块
│       ├── __init__.py
│       ├── logger.py           # 日志工具
│       └── health_check.py     # 健康检查
├── data/                       # 数据目录
│   ├── db/                     # SQLite数据库文件
│   ├── uploads/                # 人工上传文件目录
│   └── backup/                 # 数据备份目录
├── logs/                       # 日志目录
│   ├── app.log
│   ├── collector.log
│   └── error.log
└── docs/                       # 文档
    ├── plan.md
    └── architecture.md         # 本文档
```

---

## 四、模块划分与职责

### 4.1 数据采集模块 (`src/collectors/`)

| 模块 | 职责 | 数据源 |
|------|------|--------|
| `futures_collector.py` | 期货行情、仓单、持仓数据采集 | TqSdk / 大商所API |
| `spot_collector.py` | 鸡蛋现货、玉米、豆粕价格采集 | 生意社爬虫 |
| `industrial_collector.py` | 产业数据人工录入接口 | 接收CSV/JSON上传 |

### 4.2 数据存储模块 (`src/storage/`)

| 模块 | 职责 |
|------|------|
| `database.py` | 数据库连接池管理，SQLite/MySQL切换 |
| `models.py` | SQLAlchemy ORM模型定义 |
| `crud.py` | 数据增删改查封装 |

### 4.3 预警分析模块 (`src/analysis/`)

| 模块 | 职责 |
|------|------|
| `rule_engine.py` | 预警规则匹配引擎 |
| `indicators.py` | 指标计算(基差、环比、同比等) |

### 4.4 消息推送模块 (`src/notification/`)

| 模块 | 职责 |
|------|------|
| `notifier.py` | 统一通知分发接口 |
| `wechat.py` | 企业微信群机器人Webhook |
| `feishu.py` | 飞书群机器人Webhook |

### 4.5 定时任务模块 (`src/scheduler/`)

| 任务 | 执行频率 | 说明 |
|------|----------|------|
| 期货行情采集 | 交易日9:00、15:40 | 盘前+盘后 |
| 现货价格采集 | 每日10:00 | |
| 仓单数据采集 | 每日16:00 | |
| 预警规则检查 | 每次数据更新后 | |
| 数据备份 | 每周日02:00 | |

### 4.6 API接口模块 (`src/api/`)

详见「五、API契约定义」

---

## 五、API契约定义

### 5.1 通用响应结构

```typescript
interface ApiResponse&lt;T&gt; {
  code: number;       // 状态码: 200-成功, 400-请求错误, 500-服务器错误
  message: string;    // 提示信息
  data: T;            // 响应数据
  timestamp: number;  // 时间戳
}
```

---

### 5.2 期货数据接口 (`/api/futures`)

#### 获取期货实时行情
- **Method**: `GET`
- **Path**: `/api/futures/quote`
- **Description**: 获取JD2609最新行情
- **Query Params**:
  - `symbol`: string (可选, 默认: "DCE.jd2609") - 合约代码
- **Response**:
```typescript
{
  code: 200,
  message: "success",
  data: {
    symbol: string;           // 合约代码
    last_price: number;       // 最新价
    open_price: number;       // 开盘价
    high_price: number;       // 最高价
    low_price: number;        // 最低价
    close_price: number;      // 收盘价
    volume: number;           // 成交量
    open_interest: number;    // 持仓量
    timestamp: number;        // 数据时间
  },
  timestamp: 1234567890
}
```

#### 获取期货历史K线
- **Method**: `GET`
- **Path**: `/api/futures/kline`
- **Query Params**:
  - `symbol`: string (必填)
  - `period`: string (可选, 默认: "1d") - 周期: 1m/5m/1h/1d
  - `start_date`: string (可选) - 开始日期, YYYY-MM-DD
  - `end_date`: string (可选) - 结束日期, YYYY-MM-DD
- **Response**:
```typescript
{
  code: 200,
  message: "success",
  data: Array&lt;{
    datetime: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
    open_interest: number;
  }&gt;,
  timestamp: 1234567890
}
```

#### 获取仓单数据
- **Method**: `GET`
- **Path**: `/api/futures/receipt`
- **Query Params**:
  - `symbol`: string (可选, 默认: "jd")
  - `start_date`: string (可选)
  - `end_date`: string (可选)
- **Response**:
```typescript
{
  code: 200,
  message: "success",
  data: Array&lt;{
    date: string;
    symbol: string;
    receipt_qty: number;      // 仓单数量
    change: number;           // 仓单增减
  }&gt;,
  timestamp: 1234567890
}
```

---

### 5.3 现货数据接口 (`/api/spot`)

#### 获取现货价格列表
- **Method**: `GET`
- **Path**: `/api/spot/prices`
- **Query Params**:
  - `category`: string (可选) - 品种: egg/corn/soymeal
  - `start_date`: string (可选)
  - `end_date`: string (可选)
- **Response**:
```typescript
{
  code: 200,
  message: "success",
  data: Array&lt;{
    date: string;
    category: string;          // 品种
    region: string;            // 地区
    price: number;             // 价格
    unit: string;              // 单位
    source: string;            // 来源
  }&gt;,
  timestamp: 1234567890
}
```

---

### 5.4 产业数据接口 (`/api/industrial`)

#### 上传产业数据
- **Method**: `POST`
- **Path**: `/api/industrial/upload`
- **Content-Type**: `multipart/form-data`
- **Request Body**:
  - `file`: File (必填) - CSV/Excel文件
  - `data_type`: string (必填) - 数据类型: inventory/chick_sales/elimination/cold_storage
- **Response**:
```typescript
{
  code: 200,
  message: "上传成功",
  data: {
    record_count: number;      // 导入记录数
  },
  timestamp: 1234567890
}
```

#### 获取在产蛋鸡存栏
- **Method**: `GET`
- **Path**: `/api/industrial/inventory`
- **Query Params**:
  - `start_date`: string (可选)
  - `end_date`: string (可选)
- **Response**:
```typescript
{
  code: 200,
  message: "success",
  data: Array&lt;{
    date: string;
    inventory: number;         // 在产蛋鸡存栏(万羽)
    mom: number;               // 环比(%)
    yoy: number;               // 同比(%)
  }&gt;,
  timestamp: 1234567890
}
```

---

### 5.5 预警数据接口 (`/api/alert`)

#### 获取预警列表
- **Method**: `GET`
- **Path**: `/api/alert/list`
- **Query Params**:
  - `level`: string (可选) - 预警等级: info/warning/danger
  - `status`: string (可选) - 状态: pending/resolved
  - `start_date`: string (可选)
  - `end_date`: string (可选)
- **Response**:
```typescript
{
  code: 200,
  message: "success",
  data: Array&lt;{
    id: number;
    level: string;             // 预警等级
    title: string;             // 预警标题
    content: string;           // 预警内容
    rule_id: string;           // 触发规则ID
    data_snapshot: any;        // 触发时数据快照
    status: string;            // 状态
    created_at: string;
    resolved_at: string | null;
  }&gt;,
  timestamp: 1234567890
}
```

#### 处理预警
- **Method**: `PUT`
- **Path**: `/api/alert/{id}/resolve`
- **Request Body**:
```typescript
{
  remark: string;  // 处理备注
}
```

---

### 5.6 系统管理接口 (`/api/system`)

#### 健康检查
- **Method**: `GET`
- **Path**: `/api/system/health`
- **Response**:
```typescript
{
  code: 200,
  message: "success",
  data: {
    status: "healthy" | "unhealthy";
    database: "connected" | "disconnected";
    timestamp: number;
  },
  timestamp: 1234567890
}
```

#### 获取系统日志
- **Method**: `GET`
- **Path**: `/api/system/logs`
- **Query Params**:
  - `level`: string (可选) - 日志级别: info/warning/error
  - `limit`: number (可选, 默认: 100)
- **Response**:
```typescript
{
  code: 200,
  message: "success",
  data: Array&lt;{
    timestamp: string;
    level: string;
    module: string;
    message: string;
  }&gt;,
  timestamp: 1234567890
}
```

---

## 六、数据库设计

### 6.1 数据库表结构

#### 期货行情表 (`futures_quote`)
| 字段 | 类型 | 非空 | 索引 | 说明 |
|------|------|------|------|------|
| id | INTEGER | 是 | PK | 自增ID |
| symbol | VARCHAR(20) | 是 | IDX | 合约代码 |
| datetime | DATETIME | 是 | IDX | 时间 |
| open | DECIMAL(10,2) | 是 | | 开盘价 |
| high | DECIMAL(10,2) | 是 | | 最高价 |
| low | DECIMAL(10,2) | 是 | | 最低价 |
| close | DECIMAL(10,2) | 是 | | 收盘价 |
| volume | BIGINT | 是 | | 成交量 |
| open_interest | BIGINT | 是 | | 持仓量 |
| created_at | DATETIME | 是 | | 创建时间 |

#### 仓单数据表 (`futures_receipt`)
| 字段 | 类型 | 非空 | 索引 | 说明 |
|------|------|------|------|------|
| id | INTEGER | 是 | PK | 自增ID |
| date | DATE | 是 | IDX | 日期 |
| symbol | VARCHAR(20) | 是 | IDX | 品种代码 |
| receipt_qty | INTEGER | 是 | | 仓单数量 |
| change | INTEGER | 是 | | 增减量 |
| created_at | DATETIME | 是 | | 创建时间 |

#### 现货价格表 (`spot_price`)
| 字段 | 类型 | 非空 | 索引 | 说明 |
|------|------|------|------|------|
| id | INTEGER | 是 | PK | 自增ID |
| date | DATE | 是 | IDX | 日期 |
| category | VARCHAR(20) | 是 | IDX | 品种(egg/corn/soymeal) |
| region | VARCHAR(50) | 是 | | 地区 |
| price | DECIMAL(10,2) | 是 | | 价格 |
| unit | VARCHAR(20) | 是 | | 单位 |
| source | VARCHAR(50) | 是 | | 来源 |
| created_at | DATETIME | 是 | | 创建时间 |

#### 在产蛋鸡存栏表 (`industrial_inventory`)
| 字段 | 类型 | 非空 | 索引 | 说明 |
|------|------|------|------|------|
| id | INTEGER | 是 | PK | 自增ID |
| date | DATE | 是 | IDX | 日期 |
| inventory | DECIMAL(12,2) | 是 | | 在产蛋鸡存栏(万羽) |
| mom | DECIMAL(6,2) | | | 环比(%) |
| yoy | DECIMAL(6,2) | | | 同比(%) |
| source | VARCHAR(50) | 是 | | 数据来源 |
| created_at | DATETIME | 是 | | 创建时间 |

#### 预警记录表 (`alert_record`)
| 字段 | 类型 | 非空 | 索引 | 说明 |
|------|------|------|------|------|
| id | INTEGER | 是 | PK | 自增ID |
| level | VARCHAR(20) | 是 | IDX | 预警等级(info/warning/danger) |
| title | VARCHAR(200) | 是 | | 预警标题 |
| content | TEXT | 是 | | 预警内容 |
| rule_id | VARCHAR(50) | 是 | | 触发规则ID |
| data_snapshot | JSON | | | 触发时数据快照 |
| status | VARCHAR(20) | 是 | IDX | 状态(pending/resolved) |
| remark | TEXT | | | 处理备注 |
| created_at | DATETIME | 是 | IDX | 创建时间 |
| resolved_at | DATETIME | | | 处理时间 |

#### 系统日志表 (`system_log`)
| 字段 | 类型 | 非空 | 索引 | 说明 |
|------|------|------|------|------|
| id | INTEGER | 是 | PK | 自增ID |
| timestamp | DATETIME | 是 | IDX | 时间戳 |
| level | VARCHAR(20) | 是 | IDX | 日志级别 |
| module | VARCHAR(50) | 是 | | 模块 |
| message | TEXT | 是 | | 日志内容 |
| extra | JSON | | | 附加信息 |

---

## 七、错误码定义

| 错误码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
| 1001 | 数据源连接失败 |
| 1002 | 数据采集失败 |
| 2001 | 消息推送失败 |
| 3001 | 数据库操作失败 |

---

## 八、枚举常量定义

### 预警等级 (AlertLevel)
```typescript
enum AlertLevel {
  INFO = "info",        // 信息
  WARNING = "warning",  // 警告
  DANGER = "danger"     // 危险
}
```

### 预警状态 (AlertStatus)
```typescript
enum AlertStatus {
  PENDING = "pending",    // 待处理
  RESOLVED = "resolved"   // 已处理
}
```

### 现货品种 (SpotCategory)
```typescript
enum SpotCategory {
  EGG = "egg",           // 鸡蛋
  CORN = "corn",         // 玉米
  SOYMEAL = "soymeal"    // 豆粕
}
```

### 产业数据类型 (IndustrialDataType)
```typescript
enum IndustrialDataType {
  INVENTORY = "inventory",       // 在产蛋鸡存栏
  CHICK_SALES = "chick_sales",   // 鸡苗销量
  ELIMINATION = "elimination",   // 淘汰鸡出栏
  COLD_STORAGE = "cold_storage"  // 冷库库存
}
```

---

## 九、任务拆分

### 开发任务
1. 项目初始化与目录结构搭建
2. 配置模块开发 (`config/settings.py`)
3. 数据库模型定义 (`src/storage/models.py`)
4. 数据库CRUD封装 (`src/storage/crud.py`)
5. 期货数据采集器 (`src/collectors/futures_collector.py`)
6. 现货数据采集器 (`src/collectors/spot_collector.py`)
7. 产业数据采集接口 (`src/collectors/industrial_collector.py`)
8. 预警规则引擎 (`src/analysis/rule_engine.py`)
9. 指标计算模块 (`src/analysis/indicators.py`)
10. 消息推送模块 (`src/notification/`)
11. 定时任务调度 (`src/scheduler/jobs.py`)
12. API接口开发 (`src/api/routes/`)
13. 日志与健康检查 (`src/utils/`)
14. Docker部署配置

### 测试任务
1. 数据采集接口测试
2. 数据库读写测试
3. 预警规则测试
4. 消息推送测试
5. API接口测试
6. 定时任务测试
7. 健康检查测试

