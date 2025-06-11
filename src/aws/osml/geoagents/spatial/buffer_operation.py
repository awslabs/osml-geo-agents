#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging

from shapely.geometry.base import BaseGeometry

from .spatial_transforms import buffer_geometry, calculate_minimum_precision
from .spatial_utils import create_length_limited_wkt

logger = logging.getLogger(__name__)


def buffer_operation(geometry: BaseGeometry, distance: float) -> str:
    """
    Buffer a geometry by a specified distance in meters.

    :param geometry: The geometry to buffer
    :param distance: Buffer distance in meters
    :return: A formatted string with the buffering result
    :raises ValueError: If the geometry cannot be buffered
    """
    if abs(distance) < 1.0:
        return "The buffer distance must be at least 1 meter. The geometry is unchanged."

    # Buffer the geometry
    buffered_geometry = buffer_geometry(geometry, distance)

    # Calculate minimum precision based on buffer distance and latitude
    try:
        centroid = geometry.centroid
        latitude = centroid.y
    except (AttributeError, Exception):
        logger.debug("Could not determine latitude from geometry, using default (equator)")
        latitude = 0.0

    minimum_precision = calculate_minimum_precision(distance, latitude)

    # Convert to WKT with length limitation
    wkt_result = create_length_limited_wkt(buffered_geometry, minimum_precision=minimum_precision)

    # Generate response
    return f"The input geometry has been buffered by {distance} meters. Result: {wkt_result}"
