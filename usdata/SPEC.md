# 美国经济数据 MCP Server 规格说明

## 1. 项目目标

构建一个 Model Context Protocol（MCP）服务器，为交易研究提供常用美国宏观经济数据。

服务器启动后应立即可用，不等待外部数据源完成刷新；后台异步拉取数据，并按日自动刷新。查询默认读取本地缓存，外部 API 暂时不可用时返回最后一次成功缓存及其更新时间，不伪造成功或空数据。

本阶段只定义规格，不实现代码。

## 2. 数据源可用性验证

验证时间：2026-09-06。

| 数据源 | 测试结果 | 鉴权结论 | 项目定位 |
|---|---|---|---|
| FRED API | 请求 `CPIAUCSL` 返回 HTTP 400：`api_key is not set` | 所有 Web Service 请求均需要 FRED API Key | 主要时间序列来源 |
| BEA API | `samplekey` 返回 HTTP 200，但业务错误为 `UserId is not active`；无 Key 请求未返回可用数据 | 需要有效 BEA UserID/API Key | GDP、PCE、收入和国民经济核算的权威来源 |
| Census Economic Indicators API | 元数据接口可访问；实际 MARTS 数据请求返回 `Missing Key` 页面 | 实际数据调用按需要 API Key 设计 | 零售、住房、贸易、制造业等官方明细 |
| Financial Modeling Prep | 无有效 Key 或使用 `demo` 请求均返回 HTTP 401 `Invalid API KEY` | 需要有效 FMP API Key，部分端点可能受套餐限制 | 可选的经济日历及标准化补充数据 |

### 2.1 申请入口

- FRED API Key：https://fredaccount.stlouisfed.org/apikeys
- BEA API Key：https://apps.bea.gov/api/signup/
- Census API Key：https://api.census.gov/data/key_signup.html
- FMP API Key：https://site.financialmodelingprep.com/developer/

### 2.2 实现前所需凭证

第一版核心服务需要：

```text
FRED_API_KEY=
BEA_API_KEY=
CENSUS_API_KEY=
```

FMP 为可选数据源：

```text
FMP_API_KEY=
```

未配置某个 Key 时，服务器仍应启动，但对应数据源状态必须标记为 `disabled`，查询其独占指标时返回明确错误。不得将 Key 写入源码、日志、MCP 响应或版本库。

## 3. 范围

### 3.1 第一版包含

- 常用指标目录及说明
- 最新值查询
- 历史时间序列查询
- 多指标快照
- 数据源和缓存健康状态
- 手动触发后台刷新
- 启动时异步刷新
- 每日定时异步刷新
- SQLite 持久化缓存
- 原始值、单位、频率、发布日期、修订时间和数据来源追踪

### 3.2 第一版不包含

- 高频行情、股票报价、期货或期权行情
- 自动交易、下单或投资建议
- 新闻情绪分析
- 未经授权抓取网页
- 实时推送；第一版采用 MCP 查询模式
- FOMC 声明、Fed 官员讲话、Treasury 拍卖和 EIA 库存的完整覆盖

最后一项不由当前四个数据源完整覆盖。后续可接入 Federal Reserve、U.S. Treasury 和 EIA 的官方 API/RSS。

## 4. 指标目录

### 4.1 第一优先级

| 分类 | 指标 | 首选来源 | FRED Series ID 或来源说明 | 频率 |
|---|---|---|---|---|
| 通胀 | CPI | FRED | `CPIAUCSL` | 月 |
| 通胀 | Core CPI | FRED | `CPILFESL` | 月 |
| 通胀 | PCE Price Index | BEA，FRED 备选 | BEA NIPA；FRED `PCEPI` | 月 |
| 通胀 | Core PCE Price Index | BEA，FRED 备选 | BEA NIPA；FRED `PCEPILFE` | 月 |
| 通胀 | PPI Final Demand | FRED | `PPIFIS` | 月 |
| 就业 | Nonfarm Payrolls | FRED | `PAYEMS` | 月 |
| 就业 | Unemployment Rate | FRED | `UNRATE` | 月 |
| 就业 | Average Hourly Earnings | FRED | `CES0500000003` | 月 |
| 就业 | Initial Jobless Claims | FRED | `ICSA` | 周 |
| 就业 | JOLTS Job Openings | FRED | `JTSJOL` | 月 |
| 增长 | Nominal GDP | BEA，FRED 备选 | BEA NIPA；FRED `GDP` | 季 |
| 增长 | Real GDP | BEA，FRED 备选 | BEA NIPA；FRED `GDPC1` | 季 |
| 增长 | Industrial Production | FRED | `INDPRO` | 月 |
| 消费 | Retail Sales | Census，FRED 备选 | MARTS；FRED `RSAFS` | 月 |
| 消费 | Personal Income | BEA | NIPA Personal Income and Outlays | 月 |
| 消费 | Personal Consumption Expenditures | BEA | NIPA Personal Income and Outlays | 月 |
| 消费 | Consumer Sentiment | FRED | `UMCSENT`，注意可能存在授权或发布延迟 | 月 |
| 住房 | Housing Starts | Census，FRED 备选 | New Residential Construction；FRED `HOUST` | 月 |
| 住房 | Building Permits | Census，FRED 备选 | New Residential Construction；FRED `PERMIT` | 月 |
| 住房 | New Home Sales | Census，FRED 备选 | New Residential Sales；FRED `HSN1F` | 月 |
| 住房 | Existing Home Sales | FRED | `EXHOSLUSM495S` | 月 |
| 住房 | Case-Shiller Home Price Index | FRED | `CSUSHPINSA` | 月 |
| 贸易 | U.S. Trade Balance | Census/BEA，FRED 备选 | International Trade；FRED `BOPGSTB` | 月 |
| 库存 | Business Inventories | Census，FRED 备选 | Manufacturing and Trade Inventories；FRED `BUSINV` | 月 |
| 利率 | Effective Federal Funds Rate | FRED | `FEDFUNDS` | 月 |
| 利率 | 2-Year Treasury Yield | FRED | `DGS2` | 日 |
| 利率 | 10-Year Treasury Yield | FRED | `DGS10` | 日 |
| 利率 | 10Y-2Y Treasury Spread | FRED | `T10Y2Y` | 日 |

### 4.2 第二优先级

- Durable Goods Orders：Census
- Factory Orders：Census
- Wholesale Inventories and Sales：Census
- Construction Spending：Census
- International Trade 明细：Census/BEA
- Corporate Profits：BEA
- GDP 分项及贡献：BEA
- Regional GDP and Personal Income：BEA
- 经济数据发布日期日历：优先 FMP；若套餐不支持则暂不提供

### 4.3 暂不直接覆盖

- ISM Manufacturing/Services PMI：通常需要 ISM 授权，不能假定可由 FRED 免费完整提供。
- S&P Global PMI：商业授权数据。
- ADP Employment：第三方数据及授权限制。
- Atlanta Fed GDPNow：需单独确认可用接口和使用条款。

这些指标可以保留在目录中并标记 `unavailable`，但不得以相似指标冒充。

## 5. 数据源优先级与一致性

1. 指标生产机构的官方 API 优先，例如 GDP/PCE 优先 BEA，零售和住房优先 Census。
2. FRED 作为统一时间序列入口和官方数据的备选缓存来源。
3. FMP 仅用于官方 API 不便提供的标准化日历或补充字段，不覆盖官方来源的值。
4. 同一指标从多个来源取得时，保留每个来源的原始序列，不静默合并。
5. 默认查询返回首选来源；允许调用方通过 `source` 指定来源。
6. 值发生修订时，以新版本覆盖当前查询值，同时保留刷新审计记录。

## 6. MCP 工具接口

### 6.1 `list_indicators`

列出可查询指标及其元数据。

输入：

```json
{
  "category": "inflation",
  "source": "fred",
  "available_only": true
}
```

所有字段可选。

输出字段：

- `id`：服务器内稳定标识，例如 `cpi`
- `name`
- `description`
- `category`
- `source`
- `source_series_id`
- `frequency`
- `unit`
- `seasonal_adjustment`
- `status`

### 6.2 `get_latest`

查询一个指标的最新观测值。

输入：

```json
{
  "indicator_id": "cpi",
  "source": "fred",
  "transform": "yoy"
}
```

`source` 和 `transform` 可选。`transform` 支持：

- `level`
- `mom`
- `qoq`
- `yoy`
- `annualized_qoq`

转换必须基于频率进行合法性校验。例如年度序列不能计算月环比。

输出示例：

```json
{
  "indicator_id": "cpi",
  "name": "Consumer Price Index",
  "value": 2.7,
  "unit": "percent",
  "transform": "yoy",
  "observation_date": "2026-07-01",
  "source": "fred",
  "source_series_id": "CPIAUCSL",
  "fetched_at": "2026-09-06T10:00:00Z",
  "is_stale": false
}
```

### 6.3 `get_series`

查询历史序列。

输入：

```json
{
  "indicator_id": "nonfarm_payrolls",
  "start_date": "2020-01-01",
  "end_date": "2026-09-06",
  "source": "fred",
  "transform": "level",
  "limit": 500
}
```

约束：

- 日期使用 ISO 8601。
- 默认最多返回 500 个观测值，硬上限 5000。
- 结果按日期升序。
- 缺失值返回 `null` 并保留日期，不转换为 0。

### 6.4 `get_snapshot`

一次查询多个指标的最新值，适合生成交易前宏观快照。

输入：

```json
{
  "indicator_ids": [
    "cpi",
    "core_pce",
    "nonfarm_payrolls",
    "unemployment_rate",
    "real_gdp",
    "retail_sales",
    "treasury_10y"
  ]
}
```

单个指标失败不应使整个快照失败；结果中逐项返回 `ok` 或结构化错误。

### 6.5 `get_release_calendar`

查询经济数据发布日期。

输入：

```json
{
  "start_date": "2026-09-01",
  "end_date": "2026-09-30",
  "importance": "high"
}
```

此工具依赖 FMP 或后续官方日历适配器。未配置可用数据源时返回 `feature_unavailable`，不得生成预测日期。

### 6.6 `refresh_data`

手动触发后台刷新。

输入：

```json
{
  "indicator_ids": ["cpi", "core_pce"],
  "source": null,
  "force": false
}
```

行为：

- 立即返回 `job_id`，不得阻塞至刷新完成。
- 相同范围已有刷新任务时去重。
- `force=false` 时遵守最短刷新间隔。
- 仅管理员配置允许时暴露该工具。

### 6.7 `get_refresh_status`

查询数据源、最近刷新和后台任务状态。

输出至少包含：

- 每个数据源：`enabled`、`healthy`、`last_attempt_at`、`last_success_at`
- 每个刷新任务：`job_id`、`status`、`started_at`、`finished_at`、`updated_count`、`error_count`
- 缓存统计：指标数、观测值数、最旧和最新更新时间

## 7. MCP Resources

除工具外，提供只读资源：

- `us-economy://catalog`：完整指标目录
- `us-economy://status`：服务和数据源状态
- `us-economy://methodology/{indicator_id}`：指标定义、单位、频率和来源链接

## 8. 刷新机制

### 8.1 启动行为

1. 加载配置并初始化 SQLite。
2. 注册 MCP 工具，服务立即开始接受请求。
3. 创建后台刷新任务，不阻塞 MCP 启动。
4. 若缓存为空，优先刷新第一优先级指标。
5. 若已有缓存，仅刷新超过其 TTL 的指标。

### 8.2 每日刷新

- 默认每天美东时间 `18:00` 执行一次完整刷新，配置项为 `REFRESH_TIME`。
- 时区固定使用 IANA `America/New_York`，正确处理夏令时。
- 可通过配置覆盖刷新时间，但第一版不支持任意高频轮询。
- 每个数据源限制并发数，默认 3。
- HTTP 请求超时默认 30 秒。
- 对 HTTP 429、502、503、504 使用带抖动的指数退避，最多重试 3 次。
- 401/403 不重试，立即将数据源标记为鉴权失败。
- 单一数据源或指标失败不影响其他刷新任务。

### 8.3 缓存与过期

- 查询始终优先读取 SQLite。
- 每个结果包含 `fetched_at` 和 `is_stale`。
- 日频、周频、月频、季频数据默认 TTL 均为 24 小时，因为刷新要求为每日。
- 刷新失败时继续提供最近成功数据，并将 `is_stale=true`。
- 从未成功获取的指标返回明确的 `data_unavailable`，不得返回空成功响应。
- 写入使用事务；只有完整解析和校验成功后才原子替换对应批次。

## 9. 数据模型

### 9.1 `indicators`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | TEXT PK | 稳定内部 ID |
| `name` | TEXT | 英文名称 |
| `name_zh` | TEXT | 中文名称 |
| `description` | TEXT | 指标定义 |
| `category` | TEXT | 分类 |
| `preferred_source` | TEXT | 首选来源 |
| `frequency` | TEXT | 日/周/月/季/年 |
| `unit` | TEXT | 单位 |
| `seasonal_adjustment` | TEXT | 季调说明 |
| `enabled` | INTEGER | 是否启用 |

### 9.2 `source_series`

| 字段 | 类型 | 说明 |
|---|---|---|
| `indicator_id` | TEXT | 对应指标 |
| `source` | TEXT | `fred`/`bea`/`census`/`fmp` |
| `source_series_id` | TEXT | 来源端标识 |
| `source_url` | TEXT | 官方说明页 |
| `priority` | INTEGER | 来源优先级 |
| `metadata_json` | TEXT | 来源专属参数 |

联合主键为 `(indicator_id, source)`。

### 9.3 `observations`

| 字段 | 类型 | 说明 |
|---|---|---|
| `indicator_id` | TEXT | 指标 |
| `source` | TEXT | 来源 |
| `observation_date` | TEXT | 观测日期 |
| `value` | TEXT | 使用十进制定点字符串存储，避免浮点误差 |
| `status` | TEXT | `value`/`missing` |
| `fetched_at` | TEXT | 获取时间 |
| `raw_json` | TEXT | 可选原始记录，用于排错 |

联合主键为 `(indicator_id, source, observation_date)`。

### 9.4 `refresh_runs`

记录任务级状态、开始和完成时间、更新数量及错误摘要。API Key、完整请求头和敏感 URL 参数不得写入。

## 10. 配置

```text
MCP_TRANSPORT=stdio
MCP_HOST=127.0.0.1
MCP_PORT=8000
DATABASE_PATH=./data/us_economy.sqlite3

FRED_API_KEY=
BEA_API_KEY=
CENSUS_API_KEY=
FMP_API_KEY=

REFRESH_TIME=18:00
REFRESH_TIMEZONE=America/New_York
REFRESH_ON_START=true
SOURCE_CONCURRENCY=3
HTTP_TIMEOUT_SECONDS=30
MAX_RETRIES=3
MAX_SERIES_POINTS=5000
ENABLE_MANUAL_REFRESH=true
```

环境变量优先；本地开发可以使用不提交版本库的 `.env`。仓库只提供 `.env.example`。

## 11. 技术方案

建议使用：

- Python 3.12+
- 官方 Python MCP SDK / FastMCP
- `httpx` 异步 HTTP 客户端
- `aiosqlite` SQLite 异步访问
- `pydantic-settings` 配置和输入校验
- `pytest` 与 `respx` 做 API 适配器测试

定时器优先使用单个 `asyncio` 后台循环，避免第一版引入不必要的分布式任务系统。默认 MCP 传输为 `stdio`；需要远程部署时可启用 Streamable HTTP，并默认仅监听 `127.0.0.1`。

## 12. 错误规范

错误返回统一包含：

```json
{
  "code": "source_authentication_failed",
  "message": "FRED API authentication failed",
  "source": "fred",
  "retryable": false,
  "details": null
}
```

错误代码至少包括：

- `invalid_request`
- `indicator_not_found`
- `unsupported_transform`
- `source_disabled`
- `source_authentication_failed`
- `source_rate_limited`
- `source_unavailable`
- `data_unavailable`
- `feature_unavailable`
- `refresh_already_running`

不得把外部 API Key、响应头中的敏感字段或内部堆栈暴露给 MCP 调用方。

## 13. 安全与运行约束

- 所有外部请求只允许访问预先配置的官方主机，防止 SSRF。
- 不接受调用方传入任意 URL 或任意 FRED series ID；第一版只查询指标目录中的白名单。
- API Key 仅从环境变量或运行环境的 Secret Store 读取。
- 日志对查询参数中的 `api_key`、`UserID` 和 `key` 做脱敏。
- SQLite 文件所在目录默认不对外提供静态访问。
- 手动刷新设置并发限制和冷却时间，防止滥用第三方额度。
- FMP 数据的展示和缓存必须符合其当前套餐及许可条款。

## 14. 测试要求

### 14.1 单元测试

- 四个数据源适配器的成功、超时、限流、鉴权失败和异常响应
- 缺失值处理
- 月环比、季环比、同比和年化季环比计算
- 不同频率下的非法转换
- 指标来源优先级
- 日时区和夏令时调度
- 日志及错误中的密钥脱敏

### 14.2 集成测试

- 使用模拟 HTTP 响应完成首次全量刷新
- 重启后可从 SQLite 查询缓存
- 启动刷新不阻塞 MCP 工具调用
- 部分数据源失败时其余数据正常更新
- 刷新失败后仍返回最后成功数据并标记 stale
- 手动刷新返回 `job_id`，状态最终可查询

### 14.3 可选在线冒烟测试

仅在显式设置 `RUN_LIVE_API_TESTS=1` 且提供真实 Key 时运行：

- FRED：拉取 `CPIAUCSL`
- BEA：获取数据集列表及一条 NIPA 数据
- Census：拉取一条 MARTS 或住房数据
- FMP：若配置，拉取经济日历或 GDP 指标

在线测试不得成为普通 CI 的必需步骤。

## 15. 验收标准

1. 未配置任何 API Key 时 MCP 服务器可以启动，并准确报告所有不可用来源。
2. 配置相应 Key 后，可以查询第一优先级指标的最新值和历史序列。
3. 启动过程不等待外部 API；缓存查询在刷新期间可用。
4. 每天美东时间 18:00 自动异步刷新一次。
5. 外部 API 失败不会删除或覆盖最近成功缓存。
6. 每条数据可追溯到来源、来源序列、观测日期和抓取时间。
7. 所有 MCP 输入经过类型、范围和白名单校验。
8. API Key 不出现在 Git、日志、数据库或 MCP 响应中。
9. 目标单元和集成测试全部通过。

## 16. 实施顺序

1. 建立 Python 项目、配置模型和 SQLite schema。
2. 实现 FRED 适配器及第一批指标，打通 MCP 查询链路。
3. 实现后台任务、启动刷新、日更调度和状态查询。
4. 实现 BEA 和 Census 适配器及来源优先级。
5. 视 FMP Key 套餐能力实现经济日历。
6. 完成错误处理、脱敏、测试和运行文档。

## 17. 官方参考

- FRED API：https://fred.stlouisfed.org/docs/api/fred/
- FRED API Key：https://fred.stlouisfed.org/docs/api/api_key.html
- BEA API：https://apps.bea.gov/api/
- BEA API User Guide：https://apps.bea.gov/api/_pdf/bea_web_service_api_user_guide.pdf
- Census Economic Indicators：https://www.census.gov/data/developers/data-sets/economic-indicators.html
- Census API Discovery：https://api.census.gov/data.html
- FMP Developer Documentation：https://site.financialmodelingprep.com/developer/docs/
