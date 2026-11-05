"""The same server, logging to stderr: stdout stays reserved for the protocol."""

import logging
import sys

from fastmcp import FastMCP

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
log = logging.getLogger("sql-validator-demo")

mcp = FastMCP("sql-validator-demo")


@mcp.tool()
def validate_sql(sql: str) -> str:
    """Pretend to validate a SQL statement and report the result."""
    log.info("validating %s", sql)
    return "ok"


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
