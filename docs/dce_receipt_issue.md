# 大商所仓单API问题分析与解决方案

> **日期**: 2026-06-13
> **问题**: 服务器仓单采集任务持续报错，返回404状态码
> **状态**: ✅ 已解决 - API路径已修复，但鸡蛋品种可能无仓单数据

## 一、问题现象

服务器日志显示：
```
Jun 13 16:30:02 VM-0-5-ubuntu python[766722]: 2026-06-13 16:30:02 | ERROR | dce_client:_request:195 - [DCE] HTTP错误 /delivery/warehouse/receipt: 404
Jun 13 16:30:07 VM-0-5-ubuntu python[766722]: 2026-06-13 16:30:07 | ERROR | futures_receipt_collector:collect_receipt:50 - [Receipt] API调用失败或无数据: 2026-06-12
```

## 二、问题分析

### 2.1 原因排查

经过本地测试和文档分析，发现：

1. **API路径错误**: 原代码使用的 `/delivery/warehouse/receipt` 路径不存在
2. **正确路径**: 根据官方文档，仓单日报接口的正确路径是 `/forward/publicweb/dailystat/wbillWeeklyQuotes`

### 2.2 文档分析

通过提取 `docs/大连商品交易所接口说明.docx` 文档，发现：

**正确的仓单接口**:
- URL: `http://www.dce.com.cn/dceapi/forward/publicweb/dailystat/wbillWeeklyQuotes`
- 方法: POST
- 参数: `tradeDate` (交易日期), `varietyId` (品种ID，"all"表示所有品种)

**其他交割接口**:
- 一次性交割卖方仓单查询: `/forward/publicweb/DeliveryStatistics/tcCongregateDeliveryQuotes`
- 滚动交割卖方交割意向表: `/forward/publicweb/DeliveryStatistics/rollDeliverySellerIntention`

### 2.3 测试结果

| 接口 | 状态 | 说明 |
|------|------|------|
| `/forward/publicweb/dailystat/wbillWeeklyQuotes` | ✅ 正常 | 可正常访问，返回218条数据 |
| 鸡蛋品种(jd)仓单数据 | ❌ 无数据 | 返回数据中没有鸡蛋品种 |
| 其他交割接口 | ❌ 无数据 | 鸡蛋品种无交割仓单数据 |

**返回的品种列表**:
- a: 豆一
- b: 豆二
- c: 玉米
- cs: 玉米淀粉
- eb: 苯乙烯
- eg: 乙二醇
- i: 铁矿石
- j: 焦炭
- jm: 焦煤
- l: 聚乙烯
- lg: 原木
- lh: 生猪
- m: 豆粕
- p: 棕榈油
- pg: 液化石油气
- pp: 聚丙烯
- v: 聚氯乙烯
- y: 豆油

**注意**: 列表中没有鸡蛋(jd)品种，说明鸡蛋品种可能没有仓单数据。

## 三、解决方案

### 3.1 已实施的修复

**修复API路径**:

1. 更新 `src/collectors/dce_client.py` 的 `get_warehouse_receipt` 方法：
   - 使用正确的API路径 `/forward/publicweb/dailystat/wbillWeeklyQuotes`
   - 使用POST方法
   - 正确解析返回数据结构（`entityList`字段）

2. 更新 `config/settings.py`：
   - 启用仓单采集功能（`ENABLE_RECEIPT_COLLECTION=true`）
   - 默认值改为true，因为API已修复

### 3.2 当前状态

- ✅ API接口已修复，可以正常访问
- ✅ 认证headers正确添加（apikey + Authorization）
- ⚠️ 鸡蛋品种可能没有仓单数据，需要进一步确认

### 3.3 后续建议

**方案1: 继续监测仓单数据**

虽然当前没有鸡蛋仓单数据，但建议继续运行采集任务，因为：
- 仓单数据可能在特定时期出现（如交割月）
- 其他品种的仓单数据可以作为参考

**方案2: 手动监测**

如果确实需要鸡蛋仓单数据，建议：
- 每日人工查看大商所官网：http://www.dce.com.cn/dce/channel/list/187.html
- 发现仓单数据时手动录入系统

**方案3: 使用其他数据源**

考虑使用第三方数据源获取仓单信息：
- 奇货可查等数据服务商
- 期货公司提供的仓单数据

## 四、修改文件清单

| 文件 | 修改内容 |
|------|----------|
| [src/collectors/dce_client.py](../src/collectors/dce_client.py) | 修复仓单接口路径和数据解析 |
| [config/settings.py](../config/settings.py) | 启用仓单采集功能 |
| [docs/dce_receipt_issue.md](../docs/dce_receipt_issue.md) | 更新问题分析文档 |

## 五、测试验证

**测试命令**:
```bash
python test_fixed_receipt.py
```

**测试结果**:
- ✅ API接口正常访问
- ✅ 返回218条仓单数据
- ⚠️ 鸡蛋品种数据为0条

## 六、影响评估

| 功能 | 影响 | 说明 |
|------|------|------|
| 期货行情采集 | ✅ 正常 | AKShare接口可用 |
| 现货价格采集 | ✅ 正常 | 生意社爬虫可用 |
| 仓单数据采集 | ⚠️ 正常但无数据 | API已修复，但鸡蛋品种无仓单 |
| 仓单激增预警 | ⚠️ 无法触发 | 无鸡蛋仓单数据 |
| 每日数据推送 | ✅ 正常 | 仓单部分显示"无数据" |

## 七、结论

**问题已解决**: 
- ✅ API路径错误已修复
- ✅ 认证headers正确添加
- ✅ 数据解析逻辑正确

**新发现**:
- ⚠️ 鸡蛋品种可能没有仓单数据
- 建议：继续运行采集任务，等待仓单数据出现；或使用手动录入方式

---

**相关文档**:
- [大连商品交易所接口说明.docx](../docs/大连商品交易所接口说明.docx) - 官方API文档
- [src/collectors/dce_client.py](../src/collectors/dce_client.py) - DCE客户端
- [src/collectors/futures_receipt_collector.py](../src/collectors/futures_receipt_collector.py) - 仓单采集器