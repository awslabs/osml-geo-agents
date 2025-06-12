#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
from typing import Any

from ..bedrock import ToolBase, ToolExecutionError
from ..common import Workspace

logger = logging.getLogger(__name__)


class ListTool(ToolBase):
    """
    A tool for listing all datasets in the workspace.

    This tool allows users to list all datasets currently available in their workspace.
    It returns a list of georefs for all datasets in the workspace.
    """

    def __init__(self):
        """
        Constructor for the list tool which defines the action group and function name.
        """
        super().__init__("WorkspaceActions", "LIST")

    def handler(self, event: dict[str, Any], context: dict[str, Any], workspace: Workspace) -> dict[str, Any]:
        """
        Handler for listing all datasets in the workspace.

        :param event: the Lambda input event from Bedrock
        :param context: the Lambda context object for this handler
        :param workspace: the user workspace for storing large geospatial assets
        :raises ToolExecutionError: the tool was unable to process the event
        :return: the Lambda response structure for Bedrock
        """
        logger.debug(
            f"{__name__} Received Event: ActionGroup: {event['actionGroup']}, "
            f"Function: {event['function']} with parameters: {event.get('parameters', [])}"
        )

        try:
            # Get all items in the workspace
            georefs = workspace.list_items()

            if not georefs:
                result = "No datasets found in the workspace."
            else:
                # Format the result
                result = "Datasets in the workspace:\n"
                for i, georef in enumerate(georefs, 1):
                    try:
                        # Try to get the item to include its title
                        item = workspace.get_item(georef)
                        title = item.properties.get("title", "Untitled")
                        result += f"{i}. {georef} - {title}\n"
                    except Exception:
                        # If we can't get the item details, just show the georef
                        result += f"{i}. {georef}\n"

            return self.create_action_response(event, result)

        except ToolExecutionError as txe:
            # ToolExecutionErrors contain informative messages that can be relayed back to the
            # orchestration agent to help the user understand what went wrong.
            raise txe
        except Exception as e:
            logger.error("A generic / unexpected exception has been thrown by the list processing")
            logger.exception(e)
            raise ToolExecutionError(f"Failed to list datasets: {str(e)}") from e
