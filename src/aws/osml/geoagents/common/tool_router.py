#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
from typing import Any

from .tool_base import ToolBase
from .tool_registry import ToolRegistry
from .workspace import Workspace

logger = logging.getLogger(__name__)


class ToolRouter:
    """
    This class routes Lambda input events from Bedrock to the tool that is registered to
    provide a response. It also manages the creation of a workspace for this user or session
    which will give the tool access to the geospatial information that exists outside of the
    context window.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        workspace_bucket_name: str,
        workspace_local_cache: str,
    ):
        """
        Constructor for the router.

        :param tool_registry: the set of registered geospatial tools
        :param workspace_bucket_name: the name of the S3 bucked used by the workspace
        :param workspace_local_cache: the local directory that can be used for ephemeral storage
        """
        self.tool_registry = tool_registry
        self.workspace_bucket_name = workspace_bucket_name
        self.workspace_local_cache = workspace_local_cache

    def handle_request(self, event: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """
        Routes a Lambda input event/context from Bedrock to the correct tool which provides a response.

        :param event: the Lambda input event from Bedrock
        :param context: he Lambda context object for the event
        :return: the Lambda response structure for Bedrock
        """
        try:
            tool = self.tool_registry.find_tool(event["actionGroup"], event["function"])
            if not tool:
                raise ValueError(f"Unknown action group or function: {event['actionGroup']} - {event['function']}")

            # TODO: Consider managing the lifecycle of workspaces for a session differently than for users.
            #       Session workspaces should expire much more quickly and clients that create them may
            #       create a lot of them.
            workspace = Workspace(
                ToolBase.get_requesting_user(event), self.workspace_bucket_name, self.workspace_local_cache
            )

            return tool.handler(event, context, workspace)

        except Exception as e:
            error_response = ToolBase.create_action_response(event, str(e), is_error=True)
            return error_response
