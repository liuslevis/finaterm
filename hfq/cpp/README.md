# hfq C++ 引擎（Windows 原生加速）

将 UI 迁移到 C++/Windows 的第一步：**数据引擎**。它读取 Python 侧生成的
列式二进制缓存，以 SoA（Structure-of-Arrays）常驻内存，彻底避免 Python
「每事件一个 dict」的开销。

## 为什么这样分层

实测瓶颈（`600000.SH`，128,528 事件 / 4,980 帧）：

| 路径 | 加载耗时 |
|---|---|
| Python 冷解析（7z 抽取 + GBK CSV） | ~681 ms |
| Python 列式缓存（重建 dict） | ~328 ms |
| **C++ 引擎读同一 `.bin`（SoA）** | **~4.5 ms** |

即：慢的根源是 Python 的对象开销，而非磁盘或算法。C++ 以列式数组直接
`memcpy` 进内存，加载快 ~70×，`summarize` 1 ms、`build_ladder` 8 ms。

## 数据格式

列式缓存由 `app/data.py::_encode_stock` 生成，落在
`cache/<code>/_cache_v1.bin`（首次解析某股票时自动写入）。小端，布局见
`hfq_engine.h` 顶部注释。价格统一存 `int32 = 价 × 10000`。

## 构建

需要一个自带的 MinGW g++（本仓库通过 conda 环境 `hfqcpp` 提供，无需管理员 / VS / Windows SDK）：

```
conda create -n hfqcpp -c conda-forge m2w64-toolchain make cmake
cd hfq\cpp
build.bat
```

## 运行 / 对照

```
hfq_cli.exe ..\cache\600000.SH\_cache_v1.bin 150000000
```

输出汇总统计 / 十档累积阶梯 / 指定时刻盘口 + 各阶段耗时（JSON）。已与
Python 版逐字段对照一致（`summarize` / `build_ladder` / `order_book_at`）。

## 引擎 API（`hfq_engine.h`）

- `StockData::load(path)` — 读 `.bin` 到列式数组
- `summarize()` — 成交量/额（买/卖，万元），全事件计数
- `build_ladder()` — 按价位聚合委托量/撤单量，价降序
- `order_book_at(t)` — 对 `q_t` 二分取最近十档快照

## 下一步：原生 UI（ImGui + ImPlot）

引擎已就绪，界面层建议用 **Dear ImGui + ImPlot**（GLFW + OpenGL3 后端，
无需 DirectX SDK；GCC 5.3 可编译，二者以 C++11 为目标）：

1. `conda install -n hfqcpp -c conda-forge glfw`（或 vendored GLFW）。
2. 拉取 ImGui + ImPlot 源码到 `cpp/third_party/`。
3. `main.cpp`：创建窗口 → 每帧用引擎数据绘制
   - ImPlot 散点（委托地图，GPU 渲染，百万点无压力）
   - 表格（逐笔主表 / 委托明细，虚拟化滚动）
   - 十档累积阶梯 + 盘口
   - 回放引擎（时间游标推进，直接读列式数组）
4. 数据保持进程内，零 JSON 序列化。

Web 版（Python + ECharts）继续作为正确性对照与轻量演示保留。
