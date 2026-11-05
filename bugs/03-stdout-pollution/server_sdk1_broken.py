"""The same broken server on the MCP Python SDK 1.x, still common in the wild.

Run through `uv run --with "mcp<2"` by run.py, so it does not touch the
project's pinned SDK 2.x.
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("sql-validator-demo")


@mcp.tool()
def validate_sql(sql: str) -> str:
    """Pretend to validate a SQL statement and report the result."""
    print(f"debug: validating {sql}")  # writes to stdout, the protocol channel
    return "ok"


if __name__ == "__main__":
    mcp.run(transport="stdio")
