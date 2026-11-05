"""Bug 05: cold start of a uvx-launched MCP server.

Two modes:

  measure     wait as long as it takes and report the time to the first
              response, so cold and warm starts can be compared
  --timeout   behave like a client with a startup timeout: if no response
              arrives in time, give up and close stdin, then show what the
              server sends back once it finally starts

    uv cache clean                                              # make it cold
    uv run python bugs/05-cold-start/measure.py                 # measure
    uv run python bugs/05-cold-start/measure.py --timeout 8     # reproduce the failure
    uv run python bugs/05-cold-start/measure.py --timeout 8 --tool-call

By default the request is server/discover, which does not touch the database,
so ClickHouse is optional. --tool-call sends list_databases, the call of the
original incident, and needs ClickHouse on 8123.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from client.stdio_client import RawStdioClient, meta  # noqa: E402

SERVER = ["uvx", "mcp-clickhouse"]
ENV = dict(
    os.environ,
    CLICKHOUSE_HOST="localhost",
    CLICKHOUSE_PORT="8123",
    CLICKHOUSE_SECURE="false",
    CLICKHOUSE_USER="default",
    CLICKHOUSE_PASSWORD="",
)
DISCOVER = {"jsonrpc": "2.0", "id": 1, "method": "server/discover", "params": {"_meta": meta()}}
TOOL_CALL = {
    "jsonrpc": "2.0", "id": 1, "method": "tools/call",
    "params": {"name": "list_databases", "arguments": {}, "_meta": meta()},
}
NO_LIMIT = 300.0  # seconds; generous enough for a cold download


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--timeout", type=float, help="give up after this many seconds")
    parser.add_argument("--tool-call", action="store_true",
                        help="send tools/call list_databases instead of server/discover "
                             "(needs ClickHouse on 8123)")
    args = parser.parse_args()

    start = time.monotonic()
    client = RawStdioClient(SERVER, env=ENV)
    client.send(TOOL_CALL if args.tool_call else DISCOVER)
    response = client.wait_for(1, timeout=args.timeout or NO_LIMIT)
    waited = time.monotonic() - start

    if response is not None:
        client.close()
        print(f"\n=> first response after {waited:.2f}s")
        return

    print(f"\n=> no response after {waited:.2f}s: the client gives up and closes stdin")
    late = client.close(grace=NO_LIMIT)
    total = time.monotonic() - start
    message = next((json.loads(line) for line in late if line.startswith("{")), None)
    if message is None:
        print(f"=> the server exited after {total:.2f}s without answering")
    elif "error" in message:
        error = message["error"]
        print(f"=> {total:.2f}s after launch the server cancelled the abandoned request: "
              f"{error['code']} {error['message']!r}, which looks like a server failure")
    else:
        print(f"=> {total:.2f}s after launch the server answered a request nobody is waiting for")


if __name__ == "__main__":
    main()
