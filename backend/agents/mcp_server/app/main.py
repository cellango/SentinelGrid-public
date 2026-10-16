"""Main entry point for SentinelGrid MCP Server."""

import asyncio
import logging
import os
from mcp.server.stdio import stdio_server

from app.core.config import settings
from app.servers.core_server import create_core_server

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Run the MCP server via stdio."""
    logger.info(f"Starting SentinelGrid MCP Server v{settings.VERSION}")
    
    # Get tenant_id and user_id from environment (set by calling application)
    tenant_id = os.getenv("MCP_TENANT_ID", "")
    user_id = os.getenv("MCP_USER_ID", "")
    
    if not tenant_id:
        logger.warning("MCP_TENANT_ID not set, using empty string")
    if not user_id:
        logger.warning("MCP_USER_ID not set, using empty string")
    
    # Create MCP server
    server = create_core_server(tenant_id=tenant_id, user_id=user_id)
    
    logger.info("MCP Server ready")
    
    # Run server via stdio
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())

