#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging

from shapely.geometry.base import BaseGeometry

from .spatial_transforms import calculate_minimum_precision, translate_geometry
from .spatial_utils import create_length_limited_wkt

logger = logging.getLogger(__name__)


def translate_operation(geometry: BaseGeometry, distance: float, heading: float) -> str:
    """
    Translate a geometry by a specified distance and heading.

    :param geometry: The geometry to translate
    :param distance: Distance to translate in meters
    :param heading: Heading in degrees (0 = North, 90 = East, etc.)
    :return: A formatted string with the translation result
    :raises ValueError: If the geometry cannot be translated or heading is invalid
    """
    # Validate heading is between 0 and 360 degrees
    if heading is None or heading < 0 or heading >= 360:
        raise ValueError("Heading must be between 0 (inclusive) and 360 (exclusive) degrees")

    # Translate the geometry
    translated_geometry = translate_geometry(geometry, distance, heading)

    # Calculate minimum precision based on translation distance and latitude
    try:
        centroid = geometry.centroid
        latitude = centroid.y
    except (AttributeError, Exception):
        logger.debug("Could not determine latitude from geometry, using default (equator)")
        latitude = 0.0

    minimum_precision = calculate_minimum_precision(distance, latitude)

    # Convert to WKT with length limitation
    wkt_result = create_length_limited_wkt(translated_geometry, minimum_precision=minimum_precision)

    # Generate response
    return f"The input geometry has been translated by {distance} meters at heading {heading} degrees. Result: {wkt_result}"
