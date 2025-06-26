#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
from typing import Any

from s3fs import S3FileSystem

from ..common import Workspace
from .tool_base import ToolBase, ToolExecutionError
from .tool_registry import ToolRegistry

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
            user_id = ToolBase.get_requesting_user(event)
            logger.warning("User_id hardcoded to shared for early development testing")
            user_id = "shared"

            try:
                s3fs = S3FileSystem(anon=False)
                workspace = Workspace(filesystem=s3fs, prefix=f"{self.workspace_bucket_name}/{user_id}")
            except Exception as e:
                logger.error(f"Error creating S3 filesystem for workspace: {str(e)}", exc_info=True)
                raise ToolExecutionError("Failed to connect to the S3 workspace bucket.")

            return tool.handler(event, context, workspace)

        except ToolExecutionError as txe:
            error_response = ToolBase.create_action_response(event, txe.message, is_error=True)
            return error_response
        except Exception as e:
            error_response = ToolBase.create_action_response(event, str(e), is_error=True)
            return error_response
