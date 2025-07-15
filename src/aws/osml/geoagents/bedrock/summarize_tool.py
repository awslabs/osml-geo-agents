#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
from typing import Any

from ..common import Workspace
from ..spatial import summarize_operation
from .common_parameters import CommonParameters
from .tool_base import ToolBase, ToolExecutionError

logger = logging.getLogger(__name__)


class SummarizeTool(ToolBase):
    """
    A tool capable of generating natural language descriptions of columns in a geodataframe.
    It allows GenAI agents to respond to queries like:
    "What columns are available in dataset stac:dataset-a and what do they represent?"
    """

    def __init__(self):
        """
        Constructor for the spatial tool which defines the action group and function name that will be
        routed to this handler.
        """
        super().__init__("SpatialReasoning", "SUMMARIZE")

    def handler(self, event: dict[str, Any], context: dict[str, Any], workspace: Workspace) -> dict[str, Any]:
        """
        This is the implementation of the geospatial summarize event handler. It takes a geospatial reference
        as a parameter, loads the dataset, and returns a natural language description of the columns and their
        metadata.

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
            # Parse and validate the required parameters
            dataset_georef = CommonParameters.parse_dataset_georef(event, is_required=True)
            if dataset_georef is None:
                raise ToolExecutionError(
                    "Missing required parameter: 'dataset'. "
                    "The parameter must be a valid geo data reference encoded as a string."
                )

            # Call the operation function
            summary = summarize_operation(dataset_reference=dataset_georef, workspace=workspace)

            return self.create_action_response(event, summary, is_error=False)

        except ToolExecutionError as txe:
            # ToolExecutionErrors contain informative messages that can be relayed back to the
            # orchestration agent to help the user understand what went wrong.
            raise txe
        except Exception as e:
            logger.error("A generic / unexpected exception has been thrown by the summarize processing")
            logger.exception(e)
            raise ToolExecutionError(f"Unable to summarize the dataset: {str(e)}")
