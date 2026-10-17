"""Discovery-only stdio source preview; no environment-supplied authority."""

import asyncio
import logging
from mcp.server.stdio import stdio_server
from app.servers.core_server import create_core_server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    logger.info("MCP source preview: tool execution is unavailable")
    # MCP_TENANT_ID/MCP_USER_ID are not authentication. A future admitted
    # transport must derive immutable context from verified server identity.
    server = create_core_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
