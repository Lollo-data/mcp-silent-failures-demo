"""Bug 02: responses matched to the wrong request.

Two validation requests are sent without waiting. The slow one (a JOIN) goes
first, the fast one (a DROP) second; the server answers the fast one first.

  broken  reads "the next line" as the answer to each request, in send order
  fixed   matches every response to its request by id

    uv run python bugs/02-request-ids/run.py            # both
    uv run python bugs/02-request-ids/run.py broken     # just one
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from client.stdio_client import RawStdioClient, meta  # noqa: E402

HERE = Path(__file__).resolve().parent
SERVER = [sys.executable, str(HERE / "server.py")]
QUERIES = {
    1: "SELECT * FROM orders JOIN customers USING (customer_id)",
    2: "DROP TABLE customers",
}
EXPECTED = {1: "ok", 2: "rejected: only SELECT is allowed"}


def send_all(client: RawStdioClient) -> None:
    for request_id, sql in QUERIES.items():
        client.send({
            "jsonrpc": "2.0", "id": request_id, "method": "tools/call",
            "params": {"name": "validate_sql", "arguments": {"sql": sql}, "_meta": meta()},
        })


def verdict(message: dict | None) -> str:
    if not message or "result" not in message:
        return "(no answer)"
    return message["result"]["content"][0]["text"]


def broken() -> dict[int, str]:
    """The naive client: the next line on stdout is the answer to the next request."""
    client = RawStdioClient(SERVER)
    send_all(client)
    verdicts = {}
    for request_id in QUERIES:
        line = client.read_line(timeout=10)
        verdicts[request_id] = verdict(json.loads(line) if line else None)
    client.close()
    return verdicts


def fixed() -> dict[int, str]:
    """Correlate by id: each response goes to the request that carries the same id."""
    client = RawStdioClient(SERVER)
    send_all(client)
    responses = client.collect(list(QUERIES), timeout=10)
    client.close()
    return {request_id: verdict(responses.get(request_id)) for request_id in QUERIES}


def report(variant: str, verdicts: dict[int, str]) -> None:
    print()
    if any(v == "(no answer)" for v in verdicts.values()):
        print("=> no answer from the server: this run proves nothing, check that it starts")
        return
    for request_id, sql in QUERIES.items():
        got = verdicts[request_id]
        mark = "OK   " if got == EXPECTED[request_id] else "WRONG"
        print(f"[{mark}] {sql!r:60} -> {got}")
    if all(verdicts[i] == EXPECTED[i] for i in QUERIES):
        print("=> every verdict belongs to its own query")
    else:
        print("=> verdicts swapped: the DROP is marked valid, and no error was raised")


if __name__ == "__main__":
    variants = sys.argv[1:] or ["broken", "fixed"]
    for variant in variants:
        if variant not in ("broken", "fixed"):
            sys.exit("usage: run.py [broken|fixed ...]")
        print(f"\n=== {variant.upper()}")
        report(variant, broken() if variant == "broken" else fixed())
