#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import os
from typing import Any

from .common import ToolRegistry, ToolRouter


def create_tool_router() -> ToolRouter:
    """
    This is the setup function for the Lambda event handler.

    :return: a ToolRouter capable of sending events to any available tool.
    """

    tool_registry = ToolRegistry()

    from .workspace import ListTool, LoadTool, UnloadTool

    tool_registry.register_tool(ListTool())
    tool_registry.register_tool(LoadTool())
    tool_registry.register_tool(UnloadTool())

    from .spatial import ClusterTool, CorrelationTool, FilterTool, SampleTool, SummarizeTool

    tool_registry.register_tool(ClusterTool())
    tool_registry.register_tool(CorrelationTool())
    tool_registry.register_tool(FilterTool())
    tool_registry.register_tool(SampleTool())
    tool_registry.register_tool(SummarizeTool())

    return ToolRouter(
        tool_registry=tool_registry,
        workspace_bucket_name=os.environ["WORKSPACE_BUCKET_NAME"],
        workspace_local_cache=os.getenv("WORKSPACE_LOCAL_CACHE", "/tmp/osml-geo-agents/cache"),
    )


def handler(event: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """
    This is the Lamda entry point for the OversightML GeoAgent Tools

    :param event: the Lambda input event from Bedrock
    :param context: the Lambda context object for this handler
    :return: the Lambda response structure for Bedrock
    """
    tool_router = create_tool_router()
    return tool_router.handle_request(event, context)
