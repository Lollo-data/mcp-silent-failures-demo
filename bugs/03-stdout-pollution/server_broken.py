"""The demo server with one innocent-looking debug print inside a tool."""

from fastmcp import FastMCP

mcp = FastMCP("sql-validator-demo")


@mcp.tool()
def validate_sql(sql: str) -> str:
    """Pretend to validate a SQL statement and report the result."""
    print(f"debug: validating {sql}")  # writes to stdout, the protocol channel
    return "ok"


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
