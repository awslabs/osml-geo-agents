#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
from typing import Literal, get_args

from shapely.geometry.base import BaseGeometry

from .spatial_utils import create_length_limited_wkt

logger = logging.getLogger(__name__)

# Define valid operation types
CombineType = Literal["union", "intersection", "difference"]


def combine_operation(geometry1: BaseGeometry, geometry2: BaseGeometry, operation_type: CombineType) -> str:
    """
    Combine two geometries using the specified operation.

    :param geometry1: The first geometry
    :param geometry2: The second geometry
    :param operation_type: Type of operation to perform (one of the OperationType values: "union", "intersection", or "difference")
    :return: A formatted string with the combination result
    :raises ValueError: If the operation type is invalid or geometries cannot be combined
    """
    # Validate operation type at runtime for safety
    if operation_type not in get_args(CombineType):
        raise ValueError(f"Operation type must be one of: {get_args(CombineType)}")

    # Validate geometries
    if geometry1 is None or geometry2 is None:
        raise ValueError("Both geometries must be provided")

    # Perform the operation
    if operation_type == "union":
        result_geometry = geometry1.union(geometry2)
    elif operation_type == "intersection":
        result_geometry = geometry1.intersection(geometry2)
    else:  # difference
        result_geometry = geometry1.difference(geometry2)

    # Convert to WKT with length limitation
    wkt_result = create_length_limited_wkt(result_geometry)

    # Generate response
    return f"The {operation_type} of the input geometries has been calculated. Result: {wkt_result}"
