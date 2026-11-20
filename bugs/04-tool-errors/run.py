"""Bug 04: tool errors that look like success.

MCP reports failures in two ways:

  protocol error   a JSON-RPC response with an `error` field
  tool error       a successful JSON-RPC response whose result has
                   `isError: true` and the error text as content

The demo sends three requests to mcp-clickhouse, misconfigured on port 9000
(the native protocol port; mcp-clickhouse speaks HTTP), and hands the same
three responses to two clients:

  naive    stops on `error`, passes everything else to the model as data
  correct  also checks `isError` and flags the text as an error. What happens
           next is the pipeline's policy: fail, retry, or hand the text to the
           model marked as an error so it can correct itself (the
           specification recommends this for errors the model can act on).

    docker compose up -d --wait
    uv run python bugs/04-tool-errors/run.py              # port 9000, misconfigured
    uv run python bugs/04-tool-errors/run.py --port 8123  # correct port, for contrast
"""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from client.stdio_client import RawStdioClient, meta  # noqa: E402

REQUESTS = {
    1: ("wrong method name", "tools/execute", {"name": "list_databases", "arguments": {}}),
    2: ("unknown tool name", "tools/call", {"name": "list_database", "arguments": {}}),
    3: ("valid call", "tools/call", {"name": "list_databases", "arguments": {}}),
}


def text_of(message: dict) -> str:
    content = message["result"].get("content") or [{}]
    return content[0].get("text", "")


def naive(message: dict) -> str:
    """Checks only the JSON-RPC `error` field."""
    if "error" in message:
        return f"STOP  protocol error {message['error']['code']}"
    return f"MODEL {short(text_of(message))}"


def correct(message: dict) -> str:
    """Checks both kinds of failure: an error is never handed over as data."""
    if "error" in message:
        return f"STOP  protocol error {message['error']['code']}"
    if message["result"].get("isError"):
        return "ERROR tool error, not passed on as data"
    return f"MODEL {short(text_of(message))}"


def short(text: str, limit: int = 48) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", default="9000", help="CLICKHOUSE_PORT for mcp-clickhouse")
    args = parser.parse_args()

    env = dict(
        os.environ,
        CLICKHOUSE_HOST="localhost",
        CLICKHOUSE_PORT=args.port,
        CLICKHOUSE_SECURE="false",
        CLICKHOUSE_USER="default",
        CLICKHOUSE_PASSWORD="",
    )
    print(f"=== mcp-clickhouse with CLICKHOUSE_PORT={args.port}")
    client = RawStdioClient(["uvx", "mcp-clickhouse"], env=env)
    for request_id, (_, method, params) in REQUESTS.items():
        client.send({"jsonrpc": "2.0", "id": request_id, "method": method,
                     "params": {**params, "_meta": meta()}})
    responses = client.collect(list(REQUESTS), timeout=120)  # a cold uvx start is slow
    client.close()

    print(f"\n{'request':18} {'naive client':56} correct client")
    passed_errors = 0
    for request_id, (label, _, _) in REQUESTS.items():
        message = responses.get(request_id)
        if message is None:
            print(f"{label:18} (no response)")
            continue
        naive_outcome, correct_outcome = naive(message), correct(message)
        print(f"{label:18} {naive_outcome:56} {correct_outcome}")
        if naive_outcome.startswith("MODEL") and correct_outcome.startswith("ERROR"):
            passed_errors += 1

    if passed_errors:
        print(f"\n=> the naive client passed {passed_errors} error message(s) to the model "
              "as if they were data")
    else:
        print("\n=> no tool errors: both clients behave the same")


if __name__ == "__main__":
    main()
