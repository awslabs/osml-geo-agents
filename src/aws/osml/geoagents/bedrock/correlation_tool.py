#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
from typing import Any

from ..common import Workspace
from ..spatial import CorrelationTypes, correlation_operation
from .common_parameters import CommonParameters
from .tool_base import ToolBase, ToolExecutionError

logger = logging.getLogger(__name__)


class CorrelationTool(ToolBase):
    """
    A tool capable of correlating two spatial datasets using a spatial join.
    It allows GenAI agents to respond to queries like:
    "What features from dataset stac:dataset-a intersect with features from stac:dataset-b using a 100m buffer?"
    """

    def __init__(self):
        """
        Constructor for the spatial tool which defines the action group and function name that will be
        routed to this handler.
        """
        super().__init__("SpatialReasoning", "CORRELATE")

    def handler(self, event: dict[str, Any], context: dict[str, Any], workspace: Workspace) -> dict[str, Any]:
        """
        This is the implementation of the geospatial correlation event handler. It takes two geospatial references,
        a numeric distance, and an optional correlation type as parameters, loads the datasets for the references, and then
        returns a result that is a dataset with features resulting from the spatial join operation.

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
            # Parse and validate the parameters
            dataset1_georef = CommonParameters.parse_dataset_georef(event, "dataset1", is_required=True)
            dataset2_georef = CommonParameters.parse_dataset_georef(event, "dataset2", is_required=True)
            dataset1_geo_column = CommonParameters.parse_string_parameter(
                event, "dataset1_geo_column_name", is_required=False
            )
            dataset2_geo_column = CommonParameters.parse_string_parameter(
                event, "dataset2_geo_column_name", is_required=False
            )
            distance = CommonParameters.parse_distance(event, "distance")
            correlation_type = CommonParameters.parse_enum_parameter(
                event, CorrelationTypes, "correlation_type", is_required=False
            )

            # Call the operation function
            text_result = correlation_operation(
                dataset1_georef=dataset1_georef,
                dataset2_georef=dataset2_georef,
                correlation_type=correlation_type,
                distance=distance,
                dataset1_geo_column=dataset1_geo_column,
                dataset2_geo_column=dataset2_geo_column,
                workspace=workspace,
                function_name=self.function_name,
            )

            return self.create_action_response(event, text_result, is_error=False)
        except ToolExecutionError as txe:
            # ToolExecutionErrors contain informative messages that can be relayed back to the
            # orchestration agent to help the user understand what went wrong.
            raise txe
        except Exception as e:
            logger.error("A generic / unexpected exception has been thrown by the correlation processing")
            logger.exception(e)
            raise ToolExecutionError(f"Unable to correlate the datasets: {str(e)}")
