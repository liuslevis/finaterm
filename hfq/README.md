# hfq · LV2 逐笔研究终端

复现 `hfq/screenshot` 中「委托成交查看器」的 A 股 Level-2 逐笔数据回放/复盘工具。
设计规格见 [`SPEC_OPUS48.md`](SPEC_OPUS48.md)。

## 截图

![img](img/1.JPG)
![img](img/2.JPG)
![img](img/3.JPG)
![img](img/4.JPG)

## 数据源

本实现使用真实 **深交所 / 上交所 Level-2 逐笔行情**（万得 Wind CSV 格式）。
原始数据放在 `data-lv2/<交易日>.7z`（目前 59 个交易日，`20260630` … `20260921`，
每个归档含 7900+ 只 SZ/SH 标的）。新增交易日只需把对应 `<YYYYMMDD>.7z` 放入
`data-lv2/`，服务启动时自动发现。

**读取路径有两级，自动选择：**

1. **Parquet 列存**（zstd-3，按月/周分区，按 code 分片）。存在即优先使用：
   比原归档还小约 15%，随机访问快 2.3x，跨日日 K 只扫一个小文件。
2. 否则回退到 7z 归档按需抽取（归档目录见下）。

数据集位置按顺序自动探测，用第一个能打开的：

1. 环境变量 `HFQ_PARQUET_DIR`
2. 仓库内 `hfq/data-parquet/` —— **当前实际位置（C: 快盘，冷加载 0.235 s）**

7z 归档目录同理：`HFQ_ARCHIVE_DIR` → 仓库内 `hfq/data-lv2/` → **`D:\data-lv2`（当前实际位置）**。
两者可以分开放在不同盘——本机就是 Parquet 在 C:（快）、7z 归档在 D:（慢，写入 82 MB/s）。

两级的交易日取**并集**，因此可以渐进迁移——只转一部分交易日也不会丢数据。
转换与校验见 [`docs/parquet-migration.md`](docs/parquet-migration.md)。

**当前状态：59/59 个交易日已全部转换为 Parquet（278.12 GB）。**

| 指标 | 结果 |
|---|---|
| 体积 | 7z 318.19 GB / CSV 2805.71 GB → **Parquet 278.12 GB**（10.09x vs CSV，比 7z 小 1.14x） |
| 一致性 | 逐字段指纹 33/33、随机 120 只 120/120、全 59 天全列越界扫描 0 异常、HTTP 22/22 |
| 跨日日 K | 46.7–80.5 s → **0.11–1.4 s（58–590x）** |
| 磁盘 | 每「股票×日」额外占用 3.96 MB → **0.62 MB（6.4x）** |
| 单只冷加载 | Parquet 在 C: 上 0.235 s；在 D: 上 1.148 s（D: 是慢盘，见文档） |

> 转换用 `scripts/convert_all.py`（逐日 + 重试 + 时间戳日志）；临时解压必须放快盘
> （C:），只把最终 Parquet 写 D:。

```powershell
# 转全部交易日至 D:（临时解压留 C:，否则单日 40+ GB 在慢盘上会拖慢 2 倍）
python scripts/build_parquet.py --all --reuse-temp      # 默认写 hfq/data-parquet
```

每只股票含三个 GBK 编码 CSV：
- `行情.csv` —— 十档盘口快照序列（分时/盘口来源）
- `逐笔委托.csv` —— 逐笔委托（含上交所撤单，类型 A=新增/D=撤单）
- `逐笔成交.csv` —— 逐笔成交（深交所撤单为成交代码 `C`）

价格单位为「元 × 10000」，时间为 `HHMMSSmmm`。深交所委托号（交易所委托号）与
成交编号共享同一 ApplSeqNum 序列，合并排序即得逐笔主表的精确时序。

> 数据质量提示：`16xxxx.SZ` 基金的部分 `行情.csv` 首帧把「成交量/成交额」写成了
> `2^64 - n` 形式的越界值。Parquet 数据集不收录这两列（应用也不消费），因此不受影响。

## 运行

```powershell
cd hfq
python server.py            # 默认 http://127.0.0.1:8770
```

依赖：`py7zr`（从 7z 归档按需抽取单只股票）。仅本机监听。
首次加载某只股票（某交易日）会从对应归档抽取三个 CSV 到 `cache/<交易日>/<code>/` 并解析（约 1 秒），
随后走内存缓存 +（按 交易日×代码 键的）列式二进制缓存 `cache/<交易日>/<code>/_cache_vN.bin`。

环境变量：`HFQ_HOST`（默认 127.0.0.1）、`HFQ_PORT`（默认 8770）。

## 功能

| 面板 | 说明 |
|---|---|
| 委托成交查看器 | 逐笔主表（委托/成交/撤单）+ 时间/类型/数量(股)/金额(万) 区间筛选 + 委托号追踪 + 时间定位 + 汇总统计 + 基本信息 + 筛选记录（累计筛选日志）+ 多选行（Shift/Ctrl）右键统计选中范围 / 导出 CSV·TXT |
| 委托地图 | 时间×价格散点（绿买/红卖，气泡=委托量）+ 开市前显示盘前买/卖委托热力图，开市后按时间轴进度显示委托点（撮合成交/撤单的买卖委托点同时以涟漪动画消失）+ 左侧十档累积阶梯（每价位累计委托买/卖量与撤单量，叠加当前时刻十档队列）+ 回放引擎（启动/暂停/复位/倍速×1~×100）+ 键盘控制（空格 暂停/继续，←→ 拨动时间轴，↑↓ 调整倍速）+ 时间定位 + 底部委托买入/卖出明细（已成交/已撤单）|
| 逐笔成交/分时 | 分时价+均价+成交量 + 播放/暂停/复位/逐帧/倍速/时间定位 + 同步十档盘口 + 成交/委托买入/委托卖出三联明细 + 鼠标框选区间后自动过滤三联表并展示区间走势与统计 |
| 日K走势 | 跨全部已加载交易日的日 K（蜡烛 OHLC + 成交量），标注当前交易日；点击某日 K 线即切换到该交易日逐笔 |
| 交易日切换 | 顶栏「日期」下拉 + 前一天 / 后一天，按 交易日×代码 缓存，切换后基本信息/汇总/逐笔/地图/分时全部随之刷新 |
| 追踪订单 | 右键任意行或输入委托号 → 单委托号 委托→成交→撤单 生命周期 |
| 区间统计 | 点击「框选区间」后在分时图横向拖拽，松开即过滤三联表并弹出区间走势与涨幅/高低/成交量额/最大单笔/笔数；也支持主表多选行右键统计 |
| 导出 | 右键 → 导出选中（或全部）逐笔为 CSV / TXT |

## API

`GET /api/` 静态页面；JSON 接口（除 `dates` / `daily` 外均接受可选 `date=<YYYYMMDD>`，缺省取最新交易日）：
`health` · `dates` · `stocks?kw=&date=` · `basic?code=&date=` · `daily?code=`（跨日日K） ·
`events?code=&date=&start=&end=&type=&min_qty=&max_qty=&min_amt=&max_amt=` ·
`ordermap?code=&date=&min_qty=&max_qty=` · `orderbook?code=&date=&t=` · `ladder?code=&date=` ·
`books?code=&date=` · `intraday?code=&date=` · `trades?code=&date=&start=&end=` ·
`orders?code=&date=&side=&start=&end=` · `track?code=&date=&order_id=` ·
`locate?code=&date=&order_id=` · `region?code=&date=&start=&end=`

> `min_amt`/`max_amt` 单位为**万元**；委托类事件按名义额（价×量）计，成交类按实际成交额计。

## 已知限制

- 日 K 走势仅覆盖 `data-lv2/` 中已放入的交易日；日 K 的 OHLC 由当日十档快照派生（非官方日线）。
- 换手率 / 流通股 / 市值 需外部静态数据，本数据集不含，界面按占位显示 `--`（不臆造）。
- 个股名称不在数据内，列表以代码展示。

## 结构

```
hfq/
├── server.py              # 标准库 HTTP 服务 + 路由（多交易日感知）
├── app/data.py            # 交易日发现、读取调度、统一事件流、统计、订单追踪、日K
├── app/parquet_store.py   # Parquet 列存层（schema / 分区路由 / 列式读取）
├── scripts/
│   ├── build_parquet.py   # 7z -> Parquet 转换器（可断点续跑）
│   ├── snapshot.py        # 改动前快照（源码 + 数据清单 + 行为指纹）
│   ├── compare_snapshot.py / compare_sweep.py / verify_daily_kline.py
│   └── bench_*.py / scan_*.py
├── docs/parquet-migration.md
├── static/                # index.html / app.js / styles.css / vendor/echarts.min.js
├── cache/<交易日>/         # 7z 回退路径的按需抽取 CSV + 二进制缓存（自动生成）
├── data-parquet/          # Parquet 列存数据集（当前实际位置，C: 盘）
├── snapshot/              # 迁移前快照与对比结果
└── data-lv2/*.7z          # 原始 7z 归档（已挪到 D:\data-lv2，仓库内为旧位置）
```
