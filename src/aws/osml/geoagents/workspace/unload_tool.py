#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
from typing import Any

from ..common import CommonParameters, ToolBase, ToolExecutionError, Workspace

logger = logging.getLogger(__name__)


class UnloadTool(ToolBase):
    """
    A tool for removing datasets from the workspace.

    This tool allows users to delete datasets from their workspace. It takes a georef
    for the dataset to delete as a parameter and removes all associated files from
    the workspace.
    """

    def __init__(self):
        """
        Constructor for the unload tool which defines the action group and function name.
        """
        super().__init__("WorkspaceActions", "UNLOAD")

    def handler(self, event: dict[str, Any], context: dict[str, Any], workspace: Workspace) -> dict[str, Any]:
        """
        Handler for removing a dataset from the workspace.

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
            # Parse the dataset georef parameter
            dataset_georef = CommonParameters.parse_dataset_georef(event, is_required=True)

            try:
                # Get the item to confirm it exists and to get its details for the response
                item = workspace.get_item(dataset_georef)
                title = item.properties.get("title", "Untitled")

                # Delete the item using the workspace method
                workspace.delete_item(dataset_georef)

                result = f"Successfully removed dataset {dataset_georef} - '{title}' from the workspace."

            except Exception as e:
                logger.error(f"Failed to remove dataset {dataset_georef}: {str(e)}")
                raise ToolExecutionError(f"Failed to remove dataset {dataset_georef}: {str(e)}")

            return self.create_action_response(event, result)

        except ToolExecutionError as txe:
            # ToolExecutionErrors contain informative messages that can be relayed back to the
            # orchestration agent to help the user understand what went wrong.
            raise txe
        except Exception as e:
            logger.error("A generic / unexpected exception has been thrown by the unload processing")
            logger.exception(e)
            raise ToolExecutionError(f"Failed to unload dataset: {str(e)}") from e
