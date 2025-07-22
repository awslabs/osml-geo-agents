#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
from typing import Any

from ..common import Workspace
from ..spatial import FilterTypes, filter_operation
from .common_parameters import CommonParameters
from .tool_base import ToolBase, ToolExecutionError

logger = logging.getLogger(__name__)


class FilterTool(ToolBase):
    """
    A tool capable of filtering a dataset to only contain results that intersect a given geometry.
    It allows GenAI agents to respond to queries like the following:

    "How many features from dataset stac:dataset-a are within the bounding area: POLYGON
    ((-76.7142 14.9457, 84.7142 14.9457, 84.7142 22.945, -76.7142 22.945, -76.7142 14.9457))?"
    """

    def __init__(self):
        """
        Constructor for the spatial tool which defines the action group and function name that will be
        routed to this handler.
        """
        super().__init__("SpatialReasoning", "FILTER")

    def handler(self, event: dict[str, Any], context: dict[str, Any], workspace: Workspace) -> dict[str, Any]:
        """
        This is the implementation of the geospatial filter event handler. It takes a geospatial reference and
        a geometry encoded as WKT as parameters, loads the dataset for the reference, and then returns a result
        that is a dataset with features that intersect the geometry.

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
            dataset_georef = CommonParameters.parse_dataset_georef(event, "dataset", is_required=True)
            filter_georef = CommonParameters.parse_dataset_georef(event, "filter", is_required=True)
            dataset_geo_column = CommonParameters.parse_string_parameter(event, "dataset_geo_column_name", is_required=False)
            filter_geo_column = CommonParameters.parse_string_parameter(event, "filter_geo_column_name", is_required=False)
            filter_type_str = CommonParameters.parse_string_parameter(event, "filter_type", is_required=False)

            # Determine the filter type
            filter_type = FilterTypes.INTERSECTS
            if filter_type_str:
                try:
                    filter_type = FilterTypes(filter_type_str.lower())
                except ValueError:
                    logger.warning(f"Invalid filter type: {filter_type_str}. Using default: {filter_type.value}")

            # Ensure the required parameters are not None
            if dataset_georef is None:
                raise ToolExecutionError("Dataset reference is required")
            if filter_georef is None:
                raise ToolExecutionError("Filter reference is required")

            # Call the operation function
            text_result = filter_operation(
                dataset_reference=dataset_georef,
                filter_reference=filter_georef,
                filter_type=filter_type,
                dataset_geo_column=dataset_geo_column,
                filter_geo_column=filter_geo_column,
                workspace=workspace,
                function_name=self.function_name,
            )

            return self.create_action_response(event, text_result, is_error=False)
        except ToolExecutionError as txe:
            # ToolExecutionErrors contain informative messages that can be relayed back to the
            # orchestration agent to help the user understand what went wrong.
            raise txe
        except Exception as e:
            logger.error("A generic / unexpected exception has been thrown by the filter processing")
            logger.exception(e)
            raise ToolExecutionError(f"Unable to filter the dataset: {str(e)}")
