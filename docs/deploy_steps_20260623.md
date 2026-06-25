# 服务器部署步骤

## 问题背景

服务器日志显示数据库缺少 `settle` 列，导致期货行情查询、保存、预警检查和每日汇总推送全部失败。

```
(sqlite3.OperationalError) no such column: futures_quote.settle
```

## 部署步骤

### 步骤 1：备份数据库

```bash
cd /home/app/egg_monitor
cp data/db/egg_monitor.db data/db/egg_monitor.db.backup_20260623
```

### 步骤 2：数据库迁移（添加 settle 列）

```bash
cd /home/app/egg_monitor
python scripts/migrate_add_settle.py
```

预期输出：
```
添加 settle 列...
迁移成功！
```

### 步骤 3：验证迁移结果

```bash
sqlite3 data/db/egg_monitor.db "PRAGMA table_info(futures_quote);"
```

预期输出应包含：
```
7|settle|NUMERIC(10,2)|0||0
```

### 步骤 4：更新代码

```bash
cd /home/app/egg_monitor
git pull origin main
```

本次更新包含：
- `src/collectors/futures_client.py` - 统一期货数据客户端
- `src/collectors/futures_collector.py` - 使用统一客户端
- `src/storage/models.py` - 添加 settle 字段
- `scripts/migrate_add_settle.py` - 数据库迁移脚本

### 步骤 5：重启服务

```bash
# 停止现有服务
sudo systemctl stop egg_monitor

# 启动服务
sudo systemctl start egg_monitor

# 检查服务状态
sudo systemctl status egg_monitor
```

### 步骤 6：验证功能

#### 6.1 测试期货行情采集

```bash
cd /home/app/egg_monitor
python -c "
from src.collectors.futures_collector import fetch_latest_quote
result = fetch_latest_quote('jd2609')
if result:
    print(f'成功: close={result[\"close\"]}, settle={result.get(\"settle\")}')
else:
    print('失败')
"
```

预期输出：
```
成功: close=4254.0, settle=4225.0
```

#### 6.2 测试完整刷新流程

```bash
cd /home/app/egg_monitor
python scripts/test_refresh_and_push.py
```

预期输出：
```
✅ 全流程成功！
✅ 数据已刷新
✅ 推送已发送
```

#### 6.3 检查日志

```bash
tail -n 50 logs/server_log.log
```

确认无错误信息：
- ✅ `[API SUCCESS] jd2609 获取今日数据成功`
- ✅ `Save one record success`（无 warning）
- ✅ `每日汇总推送成功`

### 步骤 7：监控运行

```bash
# 查看实时日志
tail -f logs/server_log.log

# 检查定时任务
sudo systemctl status egg_monitor
```

## 验收标准

| 功能 | 验收标准 |
|------|----------|
| 期货行情采集 | 大商所API成功获取数据，包含结算价 |
| 数据库保存 | 无 `no such column` 错误 |
| 预警检查 | 正常运行，无数据库错误 |
| 每日汇总推送 | 包含期货数据，无异常警报 |

## 回滚方案

如果迁移失败或出现问题：

```bash
# 停止服务
sudo systemctl stop egg_monitor

# 恢复数据库
cd /home/app/egg_monitor
cp data/db/egg_monitor.db.backup_20260623 data/db/egg_monitor.db

# 回滚代码
git checkout HEAD~1

# 启动服务
sudo systemctl start egg_monitor
```

## 注意事项

1. **迁移脚本已创建**：`scripts/migrate_add_settle.py`
2. **数据库备份**：迁移前务必备份
3. **服务重启**：代码更新后需要重启服务
4. **日志监控**：部署后持续监控日志确认无错误

## 完成时间

预计部署时间：5-10 分钟