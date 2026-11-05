# Verified versions and measurements

Checked on 5 November 2026.

| Component | Version | Notes |
| --- | --- | --- |
| MCP specification | 2026-07-28 | Stateless: no `initialize` handshake, version in `_meta`, `server/discover` |
| FastMCP | 4.1.6 | Startup banner goes to stderr; `run(..., show_banner=False)` |
| MCP Python SDK | 2.3.0 | Diverts fd 1 to stderr while serving; restores it on exit |
| MCP Python SDK (legacy) | 1.30.0 | No stdout guard |
| mcp-clickhouse | 0.7.0 | Bundles FastMCP 4.0.11; HTTP interface only (8123/8443) |

## Observations

- Request with neither handshake nor `_meta`: `-32602 "Invalid request parameters"`, empty `data`.
- Client that skips `notifications/initialized` (2025-11-25): FastMCP 4.1.6 still answers.
- `print()` in a tool, SDK 1.30 + `PYTHONUNBUFFERED=1`: the line reaches stdout before the response.
- `print()` in a tool, SDK 1.30, buffered: the line is lost (neither stdout nor stderr).
- `print()` in a tool, SDK 2.3, buffered: the line reaches stdout at shutdown, after the guard is lifted.
- mcp-clickhouse on port 9000: explicit message, returned as a successful result with `"isError": true`.
- FastMCP checks PyPI for updates at startup (`GET https://pypi.org/pypi/fastmcp/json`).

## Cold start of `uvx mcp-clickhouse` (MacBook Air M5)

| Cache state | Time to first response |
| --- | --- |
| Empty (`uv cache clean`) | 37.22 s |
| Partial (dependencies cached) | about 8 s |
| Warm | 0.55 s, 0.50 s, 0.50 s |
