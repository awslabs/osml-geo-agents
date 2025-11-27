#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import contextlib
import logging
import os

import uvicorn
from starlette import status
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from aws.osml.geoagents.mcp.mcp_server_entrypoint import configure_logging, create_mcp_server, get_workspace

# Set up logging
logger = logging.getLogger(__name__)


async def health_check(request) -> Response:
    """Health check endpoint for ECS and ALB health checks."""
    return JSONResponse({"status": "OK", "service": "geo-agents-mcp"})


async def reject_sse_requests(request) -> Response:
    """Handle GET requests - reject SSE requests but allow other GET requests."""
    accept_header = request.headers.get("accept", "")

    # Only reject GET requests specifically requesting SSE streams
    if "text/event-stream" in accept_header:
        logger.info(f"Rejecting SSE GET request from {request.client} - Accept: {accept_header}")
        return Response(
            content="Method Not Allowed: Server-Sent Events not supported",
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            headers={"Allow": "POST, OPTIONS"},
        )

    # For non-SSE GET requests, return a simple health response
    logger.info(f"Handling non-SSE GET request from {request.client} - Accept: {accept_header}")
    return await health_check(request)


def main() -> None:
    """Main entrypoint for FastMCP server."""
    # Configure logging
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    configure_logging(level=getattr(logging, log_level))

    logger.info("Starting GeoAgents MCP Server")

    # Initialize workspace
    workspace = get_workspace()

    # Create MCP server - no SSE
    mcp = create_mcp_server(workspace)
    mcp.settings.stateless_http = True
    mcp.settings.streamable_http_path = "/"
    mcp.settings.json_response = True

    # Create lifespan manager for the session manager
    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette):
        async with mcp.session_manager.run():
            yield

    # Create Starlette app with explicit GET rejection for SSE requests
    app = Starlette(
        routes=[
            Route("/health", health_check, methods=["GET"]),  # Health check endpoint
            Route("/", reject_sse_requests, methods=["GET"]),  # Handle GET requests to reject SSE
            Mount("/", app=mcp.streamable_http_app()),  # streamable-http transport for POST/OPTIONS
        ],
        lifespan=lifespan,
    )

    # Add CORS middleware for browser-based MCP clients
    app = CORSMiddleware(
        app,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "Accept",
            "X-Requested-With",
            "X-Amz-Date",
            "X-Api-Key",
            "X-Amz-Security-Token",
            "X-Amz-User-Agent",
            "mcp-session-id",
            "mcp-protocol-version",
        ],
        expose_headers=["Mcp-Session-Id"],
        allow_credentials=False,
        max_age=600,
    )

    # Get server configuration from environment
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))

    logger.info(f"Starting persistent FastMCP server on {host}:{port}")

    # Run with uvicorn for ECS persistent operation
    uvicorn.run(app, host=host, port=port, log_level=log_level.lower())


if __name__ == "__main__":
    main()
