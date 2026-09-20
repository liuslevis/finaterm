#include "hfq_engine.h"

#include <algorithm>
#include <cstring>
#include <fstream>
#include <map>
#include <stdexcept>

namespace hfq {

namespace {
// 小端读取助手（x86 为小端，直接 memcpy）
template <typename T>
static void read_col(const char* base, size_t& off, size_t total, std::vector<T>& out) {
    if (off + 8 > total) throw std::runtime_error("truncated len");
    uint64_t bytes;
    std::memcpy(&bytes, base + off, 8);
    off += 8;
    if (off + bytes > total) throw std::runtime_error("truncated col");
    out.resize(bytes / sizeof(T));
    std::memcpy(out.data(), base + off, bytes);
    off += bytes;
}
}  // namespace

bool StockData::load(const std::string& path) {
    std::ifstream f(path, std::ios::binary | std::ios::ate);
    if (!f) return false;
    std::streamsize size = f.tellg();
    f.seekg(0, std::ios::beg);
    blob_.resize(static_cast<size_t>(size));
    if (!f.read(&blob_[0], size)) return false;

    const char* base = blob_.data();
    size_t total = blob_.size();
    if (total < 12 || std::memcmp(base, "HFQ2", 4) != 0) return false;
    int32_t ver, n;
    std::memcpy(&ver, base + 4, 4);
    std::memcpy(&n, base + 8, 4);
    if (ver != 1) return false;

    try {
        size_t off = 12;
        read_col(base, off, total, aseq);
        read_col(base, off, total, ev_t);
        read_col(base, off, total, type);
        read_col(base, off, total, side);
        read_col(base, off, total, price_raw);
        read_col(base, off, total, qty);
        read_col(base, off, total, buy_id);
        read_col(base, off, total, sell_id);
        read_col(base, off, total, order_id);
        if (off + 4 > total) return false;
        int32_t m;
        std::memcpy(&m, base + off, 4);
        off += 4;
        read_col(base, off, total, q_t);
        read_col(base, off, total, q_last);
        read_col(base, off, total, q_high);
        read_col(base, off, total, q_low);
        read_col(base, off, total, q_open);
        read_col(base, off, total, q_prev);
        read_col(base, off, total, q_cum_vol);
        read_col(base, off, total, q_cum_amt);
        read_col(base, off, total, ladder_raw);
        (void)n;
        (void)m;
    } catch (const std::exception&) {
        return false;
    }
    return true;
}

Summary StockData::summarize() const {
    Summary s;
    s.count = static_cast<int64_t>(n_events());
    for (size_t i = 0; i < n_events(); ++i) {
        if (type[i] != T_DEAL) continue;
        double amt_wan = static_cast<double>(price_raw[i]) * qty[i] / 1e8;  // 万元
        if (side[i] == S_BUY) {
            s.buy_vol += qty[i];
            s.buy_amt += amt_wan;
        } else {
            s.sell_vol += qty[i];
            s.sell_amt += amt_wan;
        }
    }
    return s;
}

std::vector<LadderRow> StockData::build_ladder() const {
    // 按 order_id 聚合成交/撤单，得每笔委托的 filled/canceled，再按价位汇总。
    // 这里直接按“委托事件的价位”聚合委托量与撤单量，近似 Python 版语义。
    std::map<int32_t, LadderRow> agg;
    // filled/canceled 需要 order 维度，先建 order_id -> (side, price)
    // 简化：委托量按委托事件价位累计；撤单量按撤单事件对应委托价位累计。
    std::map<int64_t, std::pair<int8_t, int32_t>> ord;  // oid -> (side, price_raw)
    for (size_t i = 0; i < n_events(); ++i) {
        if (type[i] == T_ORDER && price_raw[i] > 0) {
            ord[order_id[i]] = {side[i], price_raw[i]};
            LadderRow& r = agg[price_raw[i]];
            r.price_raw = price_raw[i];
            if (side[i] == S_BUY) r.buy_vol += qty[i];
            else r.sell_vol += qty[i];
        }
    }
    for (size_t i = 0; i < n_events(); ++i) {
        if (type[i] != T_CANCEL) continue;
        auto it = ord.find(order_id[i]);
        if (it == ord.end()) continue;
        int32_t p = it->second.second;
        LadderRow& r = agg[p];
        r.price_raw = p;
        if (it->second.first == S_BUY) r.buy_cancel += qty[i];
        else r.sell_cancel += qty[i];
    }
    std::vector<LadderRow> out;
    out.reserve(agg.size());
    for (auto it = agg.rbegin(); it != agg.rend(); ++it) out.push_back(it->second);  // 价降序
    return out;
}

Book StockData::order_book_at(int32_t t) const {
    Book b;
    if (q_t.empty()) return b;
    // 二分：最大的 q_t[i] <= t
    size_t lo = 0, hi = q_t.size(), idx = 0;
    // upper_bound then -1
    auto ub = std::upper_bound(q_t.begin(), q_t.end(), t);
    if (ub == q_t.begin()) idx = 0;
    else idx = static_cast<size_t>((ub - q_t.begin()) - 1);
    (void)lo; (void)hi;
    b.valid = true;
    b.t = q_t[idx];
    b.last_raw = q_last[idx];
    const int32_t* L = ladder_raw.data() + idx * 40;
    for (int k = 0; k < 10; ++k) {
        b.ask_px[k] = L[2 * k];
        b.ask_qty[k] = L[2 * k + 1];
        b.bid_px[k] = L[20 + 2 * k];
        b.bid_qty[k] = L[20 + 2 * k + 1];
    }
    return b;
}

}  // namespace hfq
