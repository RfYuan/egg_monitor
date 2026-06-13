# 快速使用指南

## 一、立即开始

### 1.1 产业数据录入（本周必做）

**步骤1**: 从我的农产品网下载鸡蛋周度报告

**步骤2**: 整理数据为CSV格式，参考示例：
```csv
date,category,inventory,mom,yoy,source
2026-06-13,在产蛋鸡存栏,12.50亿羽,-2.1%,-5.3%,我的农产品网
2026-06-13,鸡苗周销量,8500万羽,-3.2%,-8.5%,我的农产品网
2026-06-13,淘汰鸡出栏,1200万羽,5.6%,-12.3%,卓创资讯
2026-06-13,冷库鸡蛋库存,3.2万吨,8.5%,15.2%,我的农产品网
```

**步骤3**: 上传到系统
```bash
python -m src.utils.industrial_uploader data/uploads/你的数据.csv
```

**步骤4**: 验证数据已入库
```bash
python scripts/init_database.py  # 查看数据库记录
```

---

### 1.2 测试每日汇总推送

```bash
python -m src.notification.daily_summary
```

检查飞书是否收到汇总消息。

---

### 1.3 测试黑天鹅监测

```bash
python -m src.utils.black_swan_monitor
```

检查飞书是否收到预警消息（如果有风险）。

---

## 二、定时任务说明

系统会自动执行以下任务：

| 时间 | 任务 | 说明 |
|------|------|------|
| 每日 09:00 | 黑天鹅监测 | 检查禽流感、抛储等关键词 |
| 每日 09:30 | 期货行情采集 | 盘前行情 |
| 每日 10:00 | 现货价格采集 | 鸡蛋、玉米、豆粕 |
| 每日 15:40 | 期货行情采集 | 盘后行情 |
| 每日 16:00 | 每日报告 | 简要推送 |
| 每日 16:30 | 每日汇总 | 详细汇总推送 |
| 每日 16:30 | 仓单数据采集 | 大商所仓单 |
| 每周五 17:00 | 持仓数据采集 | 大商所前20持仓 |
| 每周日 00:00 | 数据备份 | 备份数据库和日志 |

**启动定时任务**:
```bash
python src/main.py
```

---

## 三、数据库查看

```bash
# 查看数据库结构
python scripts/init_database.py
```

数据库位置：`data/db/egg_monitor.db`

主要表：
- `futures_quote`: 期货行情
- `futures_receipt`: 仓单数据
- `futures_holding`: 持仓数据
- `spot_price`: 现货价格
- `industrial_inventory`: 产业数据
- `alert_record`: 预警记录

---

## 四、常见问题

### Q1: 产业数据上传失败怎么办？

检查CSV格式：
- 必须包含列：`date`, `category`, `inventory`, `source`
- 可选列：`mom`, `yoy`
- 日期格式：`2026-06-13`
- 数量格式：`12.50亿羽`、`8500万羽`、`3.2万吨`

### Q2: 每日汇总没有数据怎么办？

确保以下数据源已启用：
1. 期货行情：`python src/main.py` 已运行
2. 现货价格：需要实现生意社爬虫（或手动录入）
3. 产业数据：需要手动上传CSV

### Q3: 黑天鹅监测如何启用？

当前版本仅包含关键词匹配逻辑，实际爬虫待实现。
如需启用实际监测，请实现：
- 禽病网爬虫：`src/utils/black_swan_monitor.py` 中的 `_check_qinbing()`
- 财联社爬虫：`src/utils/black_swan_monitor.py` 中的 `_check_cls()`

### Q4: 数据备份在哪里？

备份位置：`data/backup/egg_monitor_backup_*.zip`

保留策略：最近4周备份

---

## 五、飞书通知测试

```bash
# 测试飞书连接
python test_feishu.py
```

确保 `.env` 文件中配置了 `FEISHU_WEBHOOK_URL`。

---

## 六、联系方式

如有问题，请查看：
- [docs/development_summary.md](file:///d:\code\egg_monitor\docs\development_summary.md) - 开发总结
- [docs/dev_spec.md](file:///d:\code\egg_monitor\docs\dev_spec.md) - 技术规格
- [docs/plan.md](file:///d:\code\egg_monitor\docs\plan.md) - 业务规划
