# MCP silent failures: demos

Small, reproducible demos of Model Context Protocol failures that do not
produce a clear error: requests that hang, answers that look like success,
lines that vanish. Each folder under `bugs/` has a broken and a fixed version.

The client in `client/` is written by hand, without an SDK, so every message
that travels on the wire is printed.

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

Bugs 04 and 05 also need a local ClickHouse on ports 8123 and 9000.
Bugs 01 to 03 do not.

With Docker:

```bash
docker compose up -d --wait
docker compose down        # when you are done
```

Without Docker (macOS and Linux; downloads a single binary into `.clickhouse/`):

```bash
./scripts/clickhouse.sh
```

## The demos

| Folder | Failure | Run |
| --- | --- | --- |
| `bugs/01-protocol-dialect` | A request in neither protocol dialect gets an error that does not say what is missing | `uv run python bugs/01-protocol-dialect/run.py` |
| `bugs/02-request-ids` | Responses matched to the wrong request | *coming next* |
| `bugs/03-stdout-pollution` | A debug `print()` reaches the protocol channel, or vanishes | `uv run python bugs/03-stdout-pollution/run.py` |
| `bugs/04-tool-errors` | A tool error arrives as a successful result | *coming next* (evidence in `evidence/`) |
| `bugs/05-cold-start` | First run times out while `uvx` downloads the server | `uv run python bugs/05-cold-start/measure.py` |

Versions and measurements: [`docs/versions.md`](docs/versions.md).
