"""SQL validator whose response time depends on the query.

Queries with a JOIN take longer to check, as they would against a real
database. FastMCP handles requests concurrently, so a fast answer can
overtake a slow one.
"""

import asyncio

from fastmcp import FastMCP

mcp = FastMCP("sql-validator-demo")


@mcp.tool()
async def validate_sql(sql: str) -> str:
    """Pretend to validate a SQL statement and report the result."""
    if "join" in sql.lower():
        await asyncio.sleep(1.5)
    return "ok" if sql.strip().lower().startswith("select") else "rejected: only SELECT is allowed"


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
