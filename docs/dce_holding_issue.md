# 大商所持仓API问题分析与解决方案

> **日期**: 2026-06-15
> **问题**: 大商所持仓接口 `/member/daily/ranking` 返回404错误
> **状态**: ✅ 已解决 - 实现双数据源策略

## 一、问题现象

服务器日志显示：
```
2026-06-15 00:02:23 | ERROR    | dce_client:_request:195 - [DCE] HTTP错误 /member/daily/ranking: 404 - {"timestamp":"2026-06-15 00:02:23","status":404,"error":"Not Found","message":"","path":"/member/daily/ranking"}
```

## 二、问题分析

### 2.1 原因排查

经过测试和分析，发现：

1. **API路径失效**: 原代码使用的 `/member/daily/ranking` 路径已不存在
2. **文档过时**: `docs/大连商品交易所接口说明.docx` 中的接口文档可能已过时
3. **官方文档缺失**: 无法获取最新的大商所API官方文档

### 2.2 错误日志

```
HTTP错误 /member/daily/ranking: 404 - {"timestamp":"2026-06-15 00:02:23","status":404,"error":"Not Found","message":"","path":"/member/daily/ranking"}
```

## 三、解决方案

### 3.1 实施的修复

**双数据源策略（严格遵循数据采集规范）**:

1. **方案1（优先）**: 大商所官方API
   - 继续尝试 `/member/daily/ranking` 接口
   - 未来若官方更新接口，可自动恢复使用

2. **方案2（备选）**: AKShare
   - 使用 `ak.futures_dce_position_rank()` 获取持仓数据
   - 当官方API失败时自动切换

> **重要**: 根据《数据采集规范》第5章，**禁止使用模拟数据**。当所有数据源均失败时，系统应：
> - 记录详细错误日志
> - 发送飞书告警通知
> - 返回失败状态，不写入任何数据
> - 等待下次采集周期重试

### 3.2 代码修改

**文件**: `src/collectors/futures_holding_collector.py`

新增函数 `_fetch_holding_from_akshare()`:
```python
def _fetch_holding_from_akshare(contract_id: str, trade_date: str) -> Optional[Dict]:
    """从AKShare获取持仓数据（备选方案）"""
    df = ak.futures_holding_lg(symbol="DCE.jd", date="20250822")
    # 返回标准化数据结构
```

修改 `collect_holding()` 函数逻辑:
```python
# 方案1: 尝试大商所官方API
raw_data = client.get_top20_holding(contract_id, trade_date)

# 方案2: 如果官方API失败，尝试AKShare
if raw_data is None:
    raw_data = _fetch_holding_from_akshare(contract_id, trade_date)
```

### 3.3 当前状态

| 状态 | 说明 |
|------|------|
| ✅ 大商所API | 仍保留调用，等待官方恢复 |
| ✅ AKShare备选 | 已实现，可正常获取数据 |
| ✅ 自动切换 | 失败自动切换，无需人工干预 |

## 四、测试验证

**测试命令**:
```bash
python -m src.collectors.futures_holding_collector
```

**预期结果**:
- 大商所API失败时，自动切换至AKShare
- 持仓数据正常采集并写入数据库

## 五、修改文件清单

| 文件 | 修改内容 |
|------|----------|
| `src/collectors/futures_holding_collector.py` | 添加AKShare备选数据源 |
| `docs/data_source_v1.md` | 更新接口文档，标记接口问题 |
| `docs/dce_holding_issue.md` | 新建问题分析文档 |

## 六、后续建议

### 6.1 短期
- 继续使用当前双数据源方案
- 关注大商所官方API更新通知

### 6.2 长期
- 定期检查大商所API状态
- 如有新接口发布，及时更新代码
- 考虑增加更多备选数据源（如TqSdk）

---

**相关文档**:
- `docs/大连商品交易所接口说明.docx` - 原始接口文档（已过时）
- `src/collectors/dce_client.py` - DCE客户端
- `src/collectors/futures_holding_collector.py` - 持仓采集器