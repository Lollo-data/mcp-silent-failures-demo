"""Bug 01: the wrong protocol dialect.

Since spec 2026-07-28 there is no initialize handshake: every request carries
its protocol version in `_meta`. Servers still accept the older 2025-11-25
handshake. A request that follows neither is rejected with an error that
does not say what is missing.

    uv run python bugs/01-protocol-dialect/run.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from client.stdio_client import RawStdioClient, meta  # noqa: E402

SERVER = [sys.executable, str(ROOT / "server" / "demo_server.py")]


def broken() -> None:
    print("\n=== BROKEN: no handshake and no _meta")
    client = RawStdioClient(SERVER)
    client.send({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    client.read_line()
    client.close()


def fixed_stateless() -> None:
    print("\n=== FIXED (2026-07-28): discover, then every request carries _meta")
    client = RawStdioClient(SERVER)
    client.send({"jsonrpc": "2.0", "id": 1, "method": "server/discover", "params": {"_meta": meta()}})
    client.read_line()
    client.send({
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {"name": "validate_sql", "arguments": {"sql": "SELECT 1"}, "_meta": meta()},
    })
    client.read_line()
    client.close()


def fixed_legacy() -> None:
    print("\n=== FIXED (2025-11-25): the older handshake still works")
    client = RawStdioClient(SERVER)
    client.send({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "raw-client", "version": "0.1"},
        },
    })
    client.read_line()
    client.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    client.send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    client.read_line()
    client.close()


if __name__ == "__main__":
    broken()
    fixed_stateless()
    fixed_legacy()
