#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
from typing import Any, cast

from ..common import CommonParameters, ToolBase, ToolExecutionError, Workspace
from .spatial_transforms import GeometryType, buffer_geometry, calculate_minimum_precision
from .spatial_utils import create_length_limited_wkt

logger = logging.getLogger(__name__)


class BufferTool(ToolBase):
    """
    A tool that buffers a geometry by a specified distance.
    It allows GenAI agents to respond to queries like:
    "Create a 500 meter buffer around this point: POINT(-122.3321 47.6062)"
    """

    def __init__(self):
        """
        Constructor for the buffer tool which defines the action group and function name.
        """
        super().__init__("GeoGeometryOperations", "OSML-GEO-BUFFER")

    def handler(self, event: dict[str, Any], context: dict[str, Any], workspace: Workspace) -> dict[str, Any]:
        """
        Implementation of the buffer tool handler. Takes a geometry and a distance parameter,
        buffers the geometry by the specified distance, and returns the resulting geometry as a WKT string.

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
            geometry = CommonParameters.parse_shape_parameter(event, param_name="geometry", is_required=True)
            if geometry is None:
                raise ToolExecutionError("Geometry cannot be None when is_required=True")

            distance = CommonParameters.parse_distance(event, param_name="distance", is_required=True)
            if distance is None:
                raise ToolExecutionError("Distance cannot be None when is_required=True")

            # Buffer the geometry - cast to GeometryType to satisfy type checker
            buffered_geometry = buffer_geometry(cast(GeometryType, geometry), distance)

            # Calculate minimum precision based on buffer distance and latitude
            # Extract latitude from the geometry's centroid
            try:
                # Cast to GeometryType to ensure we can access centroid
                geom = cast(GeometryType, geometry)
                centroid = geom.centroid
                latitude = centroid.y
            except (AttributeError, Exception):
                # Default to equator (0 latitude) if we can't get the centroid
                logger.debug("Could not determine latitude from geometry, using default (equator)")
                latitude = 0.0

            minimum_precision = calculate_minimum_precision(distance, latitude)

            # Convert to WKT with length limitation
            wkt_result = create_length_limited_wkt(buffered_geometry, minimum_precision=minimum_precision)

            # Generate response
            text_result = f"The input geometry has been buffered by {distance} meters. Result: {wkt_result}"
            return self.create_action_response(event, text_result, is_error=False)

        except ToolExecutionError as txe:
            # ToolExecutionErrors contain informative messages that can be relayed back to the
            # orchestration agent to help the user understand what went wrong
            raise txe
        except Exception as e:
            logger.error("An unexpected exception occurred during buffer operation")
            logger.exception(e)
            raise ToolExecutionError(f"Unable to buffer the geometry: {str(e)}")
