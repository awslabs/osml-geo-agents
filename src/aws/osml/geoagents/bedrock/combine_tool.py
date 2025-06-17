#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
from typing import Any, cast

from shapely.geometry.base import BaseGeometry

from ..common import Workspace
from ..spatial import combine_operation
from .common_parameters import CommonParameters
from .tool_base import ToolBase, ToolExecutionError

logger = logging.getLogger(__name__)


class CombineTool(ToolBase):
    """
    A tool that combines two geometries using union, intersection, or difference operations.
    It allows GenAI agents to respond to queries like:
    "Find the intersection of these two polygons: POLYGON(...) and POLYGON(...)"
    """

    def __init__(self):
        """
        Constructor for the combine tool which defines the action group and function name.
        """
        super().__init__("GeoGeometryOperations", "OSML-GEO-COMBINE")

    def handler(self, event: dict[str, Any], context: dict[str, Any], workspace: Workspace) -> dict[str, Any]:
        """
        Implementation of the combine tool handler. Takes two geometries and an operation type,
        combines the geometries using the specified operation, and returns the resulting geometry as a WKT string.

        :param event: the Lambda input event from Bedrock
        :param context: the Lambda context object for this handler
        :param workspace: the user workspace for storing large geospatial assets
        :raises ToolExecutionError: if the tool was unable to process the event
        :return: the Lambda response structure for Bedrock
        """
        logger.debug(
            f"{__name__} Received Event: ActionGroup: {event['actionGroup']}, "
            f"Function: {event['function']} with parameters: {event.get('parameters', [])}"
        )

        try:
            # Parse parameters
            geometry1 = CommonParameters.parse_shape_parameter(event, param_name="geometry1", is_required=True)
            if geometry1 is None:
                raise ToolExecutionError("First geometry cannot be None when is_required=True")

            geometry2 = CommonParameters.parse_shape_parameter(event, param_name="geometry2", is_required=True)
            if geometry2 is None:
                raise ToolExecutionError("Second geometry cannot be None when is_required=True")

            operation_type = CommonParameters.parse_string_parameter(event, param_name="operation", is_required=True)
            if operation_type is None:
                raise ToolExecutionError("Operation type cannot be None when is_required=True")

            # Call the operation function - cast to BaseGeometry to satisfy type checker
            text_result = combine_operation(cast(BaseGeometry, geometry1), cast(BaseGeometry, geometry2), operation_type)

            # Create and return the response
            return self.create_action_response(event, text_result, is_error=False)

        except ToolExecutionError as txe:
            # ToolExecutionErrors contain informative messages that can be relayed back to the
            # orchestration agent to help the user understand what went wrong
            raise txe
        except ValueError as ve:
            logger.error(f"Value error during combine operation: {ve}")
            raise ToolExecutionError(str(ve))
        except Exception as e:
            logger.error("An unexpected exception occurred during combine operation")
            logger.exception(e)
            raise ToolExecutionError(f"Unable to combine the geometries: {str(e)}")
