#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
from typing import Any, cast

from shapely.geometry.base import BaseGeometry

from ..common import Workspace
from ..spatial import translate_operation
from .common_parameters import CommonParameters
from .tool_base import ToolBase, ToolExecutionError

logger = logging.getLogger(__name__)


class TranslateTool(ToolBase):
    """
    A tool that translates (moves) a geometry by a specified distance and heading.
    It allows GenAI agents to respond to queries like:
    "Move this point 500 meters northeast: POINT(-122.3321 47.6062)"
    """

    def __init__(self):
        """
        Constructor for the translate tool which defines the action group and function name.
        """
        super().__init__("GeoGeometryOperations", "OSML-GEO-MOVE")

    def handler(self, event: dict[str, Any], context: dict[str, Any], workspace: Workspace) -> dict[str, Any]:
        """
        Implementation of the translate tool handler. Takes a geometry, a distance parameter,
        and a heading parameter, translates the geometry by the specified distance and heading,
        and returns the resulting geometry as a WKT string.

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
            geometry = CommonParameters.parse_shape_parameter(event, param_name="shape", is_required=True)
            if geometry is None:
                raise ToolExecutionError("Shape cannot be None when is_required=True")

            distance = CommonParameters.parse_distance(event, param_name="distance", is_required=True)
            if distance is None:
                raise ToolExecutionError("Distance cannot be None when is_required=True")

            heading = CommonParameters.parse_numeric_parameter(event, param_name="heading", is_required=True)
            if heading is None:
                raise ToolExecutionError("Heading cannot be None when is_required=True")

            # Call the operation function - cast to BaseGeometry to satisfy type checker
            text_result = translate_operation(cast(BaseGeometry, geometry), distance, heading)

            # Create and return the response
            return self.create_action_response(event, text_result, is_error=False)

        except ToolExecutionError as txe:
            # ToolExecutionErrors contain informative messages that can be relayed back to the
            # orchestration agent to help the user understand what went wrong
            raise txe
        except ValueError as ve:
            logger.error(f"Value error during translate operation: {ve}")
            raise ToolExecutionError(str(ve))
        except Exception as e:
            logger.error("An unexpected exception occurred during translate operation")
            logger.exception(e)
            raise ToolExecutionError(f"Unable to translate the geometry: {str(e)}")
