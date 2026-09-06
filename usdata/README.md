# U.S. Economy MCP Server

为交易研究提供常用美国宏观经济时间序列的 MCP 服务。服务使用 SQLite
持久化缓存，启动后在后台刷新，并在每天美东时间 18:00 自动更新。

## 配置

服务按以下顺序读取环境变量、仓库上级目录的 `.env`、当前目录的 `.env`。
同时兼容现有变量名：

- `FED_API` 等同于 `FRED_API_KEY`
- `BEA_API` 等同于 `BEA_API_KEY`
- `CENSUS_API` 等同于 `CENSUS_API_KEY`

FRED 是当前指标数据适配器；BEA 和 Census 凭证会显示在数据源状态中，后续可
在不改变 MCP 工具契约的情况下加入官方源适配器。

## 安装与运行

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[test]"
.\.venv\Scripts\us-economy-mcp
```

默认使用 `stdio` 传输。客户端配置示例：

```json
{
  "mcpServers": {
    "us-economy": {
      "command": "C:\\Users\\david\\dev\\finance\\usdata\\.venv\\Scripts\\us-economy-mcp.exe"
    }
  }
}
```

## MCP 工具

- `list_indicators`
- `get_latest`
- `get_series`
- `get_snapshot`
- `get_release_calendar`
- `refresh_data`
- `get_refresh_status`

首次启动会异步刷新；在首批数据写入前，查询可能返回 `data_unavailable`。

