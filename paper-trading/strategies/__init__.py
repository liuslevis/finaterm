"""策略注册表：新增策略 = 在本目录加一个模块并追加到 STRATEGIES。接口见 README.md。"""
from strategies import brent_v2, qqq_dca

STRATEGIES = [brent_v2, qqq_dca]
