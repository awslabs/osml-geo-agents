# Copyright 2025 Amazon.com, Inc. or its affiliates.

"""MCP client for integration testing."""

import asyncio
import logging
import traceback
from typing import Any, Dict

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


class MCPTestClient:
    """
    MCP client for testing GeoAgent tools via HTTP.

    This client uses the Python MCP SDK to communicate with the MCP server
    over HTTP using streamable-http transport.

    Following the official MCP SDK pattern, this client uses async context managers
    for proper resource lifecycle management.
    """

    def __init__(self, endpoint: str):
        """
        Initialize the MCP test client.

        :param endpoint: The HTTP endpoint of the MCP server (ALB URL)
        """
        self.endpoint = endpoint.rstrip("/")
        logging.info(f"Initialized MCP test client for endpoint: {self.endpoint}")

    async def invoke_tool_with_connection(self, tool_name: str, arguments: Dict[str, Any], timeout: float = 60.0) -> Any:
        """
        Connect to MCP server, invoke a tool, and disconnect.

        This method follows the official MCP SDK pattern using async context managers
        to ensure proper resource cleanup.

        :param tool_name: Name of the tool to invoke
        :param arguments: Arguments to pass to the tool
        :param timeout: Timeout in seconds for the entire operation (default: 60s)
        :return: Tool execution result
        """

        async def _invoke_impl():
            async with streamablehttp_client(self.endpoint) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    return await session.call_tool(tool_name, arguments)

        try:
            result = await asyncio.wait_for(_invoke_impl(), timeout=timeout)

            # Extract result content
            if hasattr(result, "content") and len(result.content) > 0:
                content_item = result.content[0]
                if hasattr(content_item, "text"):
                    return content_item.text
                return str(content_item)

            return result

        except asyncio.TimeoutError as e:
            logging.error(f"Operation '{tool_name}' timed out after {timeout}s")
            logging.error(f"Endpoint: {self.endpoint}, Arguments: {arguments}")
            raise Exception(f"MCP operation '{tool_name}' timeout after {timeout}s") from e
        except Exception as e:
            logging.error(f"Error in invoke_tool_with_connection: {type(e).__name__}: {str(e)}")
            logging.error(f"Full traceback: {traceback.format_exc()}")
            raise
