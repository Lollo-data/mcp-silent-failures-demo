"""A healthy MCP server used as the baseline in the demos.

It stands in for the real SQL-validation server: one tool, no database, so the
demos about the protocol run without ClickHouse.
"""

import logging
import sys

from fastmcp import FastMCP

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
log = logging.getLogger("demo-server")

mcp = FastMCP("sql-validator-demo")


@mcp.tool()
def validate_sql(sql: str) -> str:
    """Pretend to validate a SQL statement and report the result."""
    log.info("validating %r", sql)
    return "ok" if sql.strip().lower().startswith("select") else "rejected: only SELECT is allowed"


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
