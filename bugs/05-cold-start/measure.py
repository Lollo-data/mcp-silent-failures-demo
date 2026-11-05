"""Bug 05: how long a uvx-launched MCP server takes to answer its first request.

Measures only the time from spawn to the first response, so cold and warm
starts can be compared.

    uv cache clean                                     # cold
    uv run python bugs/05-cold-start/measure.py
    uv run python bugs/05-cold-start/measure.py        # warm, repeat a few times

Needs a local ClickHouse on 8123 (scripts/clickhouse.sh).
"""

import json
import os
import subprocess
import time

ENV = dict(
    os.environ,
    CLICKHOUSE_HOST="localhost",
    CLICKHOUSE_PORT="8123",
    CLICKHOUSE_SECURE="false",
    CLICKHOUSE_USER="default",
    CLICKHOUSE_PASSWORD="",
)
META = {
    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
    "io.modelcontextprotocol/clientCapabilities": {},
}
REQUEST = {"jsonrpc": "2.0", "id": 1, "method": "server/discover", "params": {"_meta": META}}

start = time.monotonic()
proc = subprocess.Popen(
    ["uvx", "mcp-clickhouse"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    env=ENV,
    text=True,
)
proc.stdin.write(json.dumps(REQUEST) + "\n")
proc.stdin.flush()
first_line = proc.stdout.readline()
print(f"{time.monotonic() - start:.2f}s  {first_line.strip()[:70]}")
proc.kill()
