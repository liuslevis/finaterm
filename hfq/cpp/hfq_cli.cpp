// hfq 引擎 CLI：加载列式缓存并输出汇总统计 / 阶梯 / 盘口，用于与 Python 对照 + 基准。
// 用法: hfq_cli <path-to-_cache_v1.bin> [book_time_HHMMSSmmm]
#include <chrono>
#include <cstdio>
#include <string>

#include "hfq_engine.h"

int main(int argc, char** argv) {
    if (argc < 2) {
        std::fprintf(stderr, "usage: %s <cache.bin> [book_time]\n", argv[0]);
        return 2;
    }
    std::string path = argv[1];
    int book_t = argc >= 3 ? std::atoi(argv[2]) : 150000000;

    hfq::StockData sd;
    auto t0 = std::chrono::high_resolution_clock::now();
    if (!sd.load(path)) {
        std::fprintf(stderr, "load failed: %s\n", path.c_str());
        return 1;
    }
    auto t1 = std::chrono::high_resolution_clock::now();
    double load_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();

    auto s = sd.summarize();
    auto t2 = std::chrono::high_resolution_clock::now();
    auto ladder = sd.build_ladder();
    auto t3 = std::chrono::high_resolution_clock::now();
    auto book = sd.order_book_at(book_t);
    auto t4 = std::chrono::high_resolution_clock::now();

    // JSON 输出，便于脚本对照
    std::printf("{\n");
    std::printf("  \"events\": %lld,\n", (long long)sd.n_events());
    std::printf("  \"quotes\": %lld,\n", (long long)sd.n_quotes());
    std::printf("  \"summary\": {\"count\": %lld, \"buy_vol\": %.0f, \"sell_vol\": %.0f, "
                "\"buy_amt\": %.4f, \"sell_amt\": %.4f},\n",
                (long long)s.count, s.buy_vol, s.sell_vol, s.buy_amt, s.sell_amt);
    std::printf("  \"ladder_rows\": %lld,\n", (long long)ladder.size());
    if (!ladder.empty()) {
        const auto& r = ladder.front();
        std::printf("  \"ladder_top\": {\"price\": %.2f, \"buy_vol\": %lld, \"buy_cancel\": %lld, "
                    "\"sell_vol\": %lld, \"sell_cancel\": %lld},\n",
                    r.price_raw / hfq::PRICE_SCALE, (long long)r.buy_vol, (long long)r.buy_cancel,
                    (long long)r.sell_vol, (long long)r.sell_cancel);
    }
    if (book.valid) {
        std::printf("  \"book@%d\": {\"t\": %d, \"last\": %.2f, \"ask1\": [%.2f, %d], "
                    "\"bid1\": [%.2f, %d]},\n",
                    book_t, book.t, book.last_raw / hfq::PRICE_SCALE,
                    book.ask_px[0] / hfq::PRICE_SCALE, book.ask_qty[0],
                    book.bid_px[0] / hfq::PRICE_SCALE, book.bid_qty[0]);
    }
    std::printf("  \"timing_ms\": {\"load\": %.2f, \"summarize\": %.2f, \"ladder\": %.2f, \"book\": %.3f}\n",
                load_ms,
                std::chrono::duration<double, std::milli>(t2 - t1).count(),
                std::chrono::duration<double, std::milli>(t3 - t2).count(),
                std::chrono::duration<double, std::milli>(t4 - t3).count());
    std::printf("}\n");
    return 0;
}
