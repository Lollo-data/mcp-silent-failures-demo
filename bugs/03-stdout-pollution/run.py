"""Bug 03: a debug print() in a tool and stdout, the protocol channel.

Same print(), five cases, one tool call each. For each one the demo counts
where the debug line ends up: on stdout (the protocol channel), on stderr, or
nowhere.

  sdk1              MCP SDK 1.x with PYTHONUNBUFFERED=1 (common in Docker
                    images): the line lands on the wire before the response.
  sdk1-buffered     MCP SDK 1.x, default buffering: the SDK closes the real
                    stdout on shutdown, so the buffered line is silently lost.
  broken            MCP SDK 2.x, default buffering: the SDK diverts stdout to
                    stderr while serving, but the buffered line is flushed
                    when stdout is restored at shutdown, after the last response.
  broken-unbuffered MCP SDK 2.x with PYTHONUNBUFFERED=1: the line is written
                    at once, while the diversion is active, so it lands on
                    stderr and the protocol channel stays clean.
  fixed             log to stderr: nothing but JSON-RPC on stdout.

    uv run python bugs/03-stdout-pollution/run.py            # all five
    uv run python bugs/03-stdout-pollution/run.py sdk1       # just one
"""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from client.stdio_client import RawStdioClient, describe, meta  # noqa: E402

HERE = Path(__file__).resolve().parent
MARKER = "validating"  # appears in every debug line and log line of the servers
VARIANTS = ("sdk1", "sdk1-buffered", "broken", "broken-unbuffered", "fixed")


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


def run_sdk1(unbuffered: bool, stderr_file) -> RawStdioClient:
    server = ["uv", "run", "--no-project", "--quiet", "--with", "mcp<2",
              "python", str(HERE / "server_sdk1_broken.py")]
    client = RawStdioClient(server, env=env_with(unbuffered), stderr_file=stderr_file)
    client.send({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                   "clientInfo": {"name": "raw-client", "version": "0.1"}},
    })
    client.wait_for(1, timeout=60)  # the first run may download SDK 1.x
    client.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    call_tool(client, 2, "SELECT 1", with_meta=False)
    return client


def run_sdk2(server_name: str, unbuffered: bool, stderr_file) -> RawStdioClient:
    server = [sys.executable, str(HERE / server_name)]
    client = RawStdioClient(server, env=env_with(unbuffered), stderr_file=stderr_file)
    call_tool(client, 1, "SELECT 1", with_meta=True)
    return client


def run(variant: str) -> None:
    print(f"\n=== {variant.upper()}")
    with tempfile.TemporaryFile(mode="w+") as stderr_file:
        if variant == "sdk1":
            client = run_sdk1(unbuffered=True, stderr_file=stderr_file)
        elif variant == "sdk1-buffered":
            client = run_sdk1(unbuffered=False, stderr_file=stderr_file)
        elif variant == "broken-unbuffered":
            client = run_sdk2("server_broken.py", unbuffered=True, stderr_file=stderr_file)
        else:
            client = run_sdk2(f"server_{variant}.py", unbuffered=False, stderr_file=stderr_file)
        client.close()
        stderr_file.seek(0)
        on_stderr = sum(MARKER in line for line in stderr_file)

    on_stdout = sum(MARKER in line for line in client.transcript if describe(line).startswith("!!"))
    print(f"debug lines on stdout (protocol channel): {on_stdout}")
    print(f"debug lines on stderr:                    {on_stderr}")
    if on_stdout:
        print("=> the protocol channel is polluted")
    elif not on_stderr:
        print("=> the debug output is lost: it reached neither stream")
    else:
        print("=> clean: debug output on stderr only")


if __name__ == "__main__":
    variants = sys.argv[1:] or list(VARIANTS)
    for variant in variants:
        if variant not in VARIANTS:
            sys.exit(f"usage: run.py [{'|'.join(VARIANTS)} ...]")
        run(variant)
