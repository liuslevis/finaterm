// hfq LV2 数据引擎（C++ 版）
// 读取 Python 侧生成的列式二进制缓存 `_cache_v1.bin`，以列式（SoA）方式常驻内存，
// 计算汇总统计 / 十档累积阶梯 / 任意时刻盘口。避免 Python 每事件 dict 的巨大开销。
//
// 二进制格式（小端，见 app/data.py::_encode_stock）：
//   "HFQ2" | int32 ver | int32 n
//   9 个事件列，每列前置 uint64 字节长度：
//     aseq i64[n], t i32[n], type i8[n], side i8[n], price i32[n],
//     qty i32[n], buy i64[n], sell i64[n], oid i64[n]
//   int32 m
//   8 个行情列，每列前置 uint64 字节长度：
//     t i32[m], last i32[m], high i32[m], low i32[m], open i32[m],
//     prev i32[m], cum_vol i64[m], cum_amt i64[m]
//   ladder: uint64 len + i32[m*40]（每帧 10 卖(px,qty)+10 买(px,qty)）
#ifndef HFQ_ENGINE_H
#define HFQ_ENGINE_H

#include <cstdint>
#include <string>
#include <vector>

namespace hfq {

constexpr double PRICE_SCALE = 10000.0;
enum EventType { T_ORDER = 0, T_DEAL = 1, T_CANCEL = 2 };
enum Side { S_BUY = 0, S_SELL = 1 };

struct Summary {
    int64_t count = 0;
    double buy_vol = 0, sell_vol = 0;   // 股
    double buy_amt = 0, sell_amt = 0;   // 万元
};

struct LadderRow {
    int32_t price_raw = 0;              // 价 * 10000
    int64_t buy_vol = 0, buy_cancel = 0, sell_vol = 0, sell_cancel = 0;
};

struct Book {
    int32_t t = 0;
    int32_t last_raw = 0;
    int32_t ask_px[10] = {0}, ask_qty[10] = {0};
    int32_t bid_px[10] = {0}, bid_qty[10] = {0};
    bool valid = false;
};

// 列式股票数据（Structure-of-Arrays）
class StockData {
public:
    // 事件列
    std::vector<int64_t> aseq, buy_id, sell_id, order_id;
    std::vector<int32_t> ev_t, price_raw, qty;
    std::vector<int8_t>  type, side;
    // 行情列
    std::vector<int32_t> q_t, q_last, q_high, q_low, q_open, q_prev;
    std::vector<int64_t> q_cum_vol, q_cum_amt;
    std::vector<int32_t> ladder_raw;   // m*40

    size_t n_events() const { return aseq.size(); }
    size_t n_quotes() const { return q_t.size(); }

    // 从二进制缓存加载；失败返回 false
    bool load(const std::string& path);

    // 汇总统计（仅成交计入量/额；count 为全部事件数）
    Summary summarize() const;
    // 十档累积阶梯（按价位聚合全部委托，价>0，按价降序）
    std::vector<LadderRow> build_ladder() const;
    // 任意时刻盘口（对 q_t 做二分，取 <= t 的最近一帧）
    Book order_book_at(int32_t t) const;

private:
    std::string blob_;   // 持有文件字节，列 view 指向其中（这里为简单起见拷贝入列）
};

}  // namespace hfq

#endif  // HFQ_ENGINE_H
