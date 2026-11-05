"""Bug 03: a debug print() in a tool and stdout, the protocol channel.

Three cases, same print():

  sdk1    MCP SDK 1.x with PYTHONUNBUFFERED=1 (common in Docker images):
          the line lands on the wire before the response.
  broken  MCP SDK 2.x guards stdout while serving, but a buffered print
          escapes at shutdown, after the guard is lifted.
  fixed   log to stderr: nothing but JSON-RPC on stdout.

    uv run python bugs/03-stdout-pollution/run.py            # all three
    uv run python bugs/03-stdout-pollution/run.py sdk1       # just one
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from client.stdio_client import RawStdioClient, describe, meta  # noqa: E402

HERE = Path(__file__).resolve().parent


def env_with(unbuffered: bool) -> dict:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONUNBUFFERED"}
    if unbuffered:
        env["PYTHONUNBUFFERED"] = "1"
    return env


def call_tool(client: RawStdioClient, request_id: int, sql: str, with_meta: bool) -> None:
    params = {"name": "validate_sql", "arguments": {"sql": sql}}
    if with_meta:
        params["_meta"] = meta()
    client.send({"jsonrpc": "2.0", "id": request_id, "method": "tools/call", "params": params})
    client.wait_for(request_id)


def run_sdk1() -> RawStdioClient:
    server = ["uv", "run", "--no-project", "--quiet", "--with", "mcp<2",
              "python", str(HERE / "server_sdk1_broken.py")]
    client = RawStdioClient(server, env=env_with(unbuffered=True))
    client.send({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                   "clientInfo": {"name": "raw-client", "version": "0.1"}},
    })
    client.wait_for(1, timeout=60)  # the first run may download SDK 1.x
    client.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    call_tool(client, 2, "SELECT 1", with_meta=False)
    return client


def run_sdk2(variant: str) -> RawStdioClient:
    server = [sys.executable, str(HERE / f"server_{variant}.py")]
    client = RawStdioClient(server, env=env_with(unbuffered=False))
    call_tool(client, 1, "SELECT 1", with_meta=True)
    call_tool(client, 2, "SELECT 2", with_meta=True)
    return client


def run(variant: str) -> None:
    print(f"\n=== {variant.upper()}")
    client = run_sdk1() if variant == "sdk1" else run_sdk2(variant)
    client.close()
    stray = [line for line in client.transcript if describe(line).startswith("!!")]
    print(f"lines on stdout that are not JSON-RPC: {len(stray)}")


if __name__ == "__main__":
    variants = sys.argv[1:] or ["sdk1", "broken", "fixed"]
    for variant in variants:
        if variant not in ("sdk1", "broken", "fixed"):
            sys.exit("usage: run.py [sdk1|broken|fixed ...]")
        run(variant)
