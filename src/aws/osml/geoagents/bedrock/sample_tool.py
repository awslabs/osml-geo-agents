#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
from typing import Any

from ..common import Workspace
from ..spatial import sample_operation
from .common_parameters import CommonParameters
from .tool_base import ToolBase, ToolExecutionError

logger = logging.getLogger(__name__)


class SampleTool(ToolBase):
    """
    A tool capable of returning a text representation of features from a geodataset.
    It allows GenAI agents to respond to queries like:
    "Show me the first 5 features from dataset georef:dataset-a"
    """

    def __init__(self):
        """
        Constructor for the spatial tool which defines the action group and function name that will be
        routed to this handler.
        """
        super().__init__("SpatialReasoning", "SAMPLE")

    def handler(self, event: dict[str, Any], context: dict[str, Any], workspace: Workspace) -> dict[str, Any]:
        """
        This is the implementation of the geospatial sample event handler. It takes a geospatial reference and
        a number of features as parameters, loads the dataset for the reference, and then returns a text
        representation of the requested number of features.

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
                    "The parameter must be a valid georeference encoded as a string."
                )

            # Get number of features parameter, defaulting to 10 if not provided
            num_features = CommonParameters.parse_numeric_parameter(
                event, "number_of_features", is_required=False, must_be_positive=True
            )

            # Call the operation function
            text_result = sample_operation(
                dataset_georef=dataset_georef, number_of_features=num_features, workspace=workspace
            )

            return self.create_action_response(event, text_result, is_error=False)

        except ToolExecutionError as txe:
            # ToolExecutionErrors contain informative messages that can be relayed back to the
            # orchestration agent to help the user understand what went wrong.
            raise txe
        except Exception as e:
            logger.error("A generic / unexpected exception has been thrown by the sample processing")
            logger.exception(e)
            raise ToolExecutionError(f"Unable to sample the dataset: {str(e)}")
