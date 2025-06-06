#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
import math
from typing import Optional, Tuple, Union, cast

import geopandas as gpd
import pyproj
from shapely.affinity import translate
from shapely.geometry import GeometryCollection, LineString, MultiLineString, MultiPoint, MultiPolygon, Point, Polygon

# Set up logger
logger = logging.getLogger(__name__)

# Type alias for shapely geometries
GeometryType = Union[Point, LineString, Polygon, MultiPoint, MultiLineString, MultiPolygon, GeometryCollection]


def _project_to_utm(
    geometry: GeometryType, utm_crs: Optional[Union[str, pyproj.CRS]] = None
) -> Tuple[GeometryType, pyproj.CRS]:
    """
    Project a geometry from WGS84 to an appropriate UTM CRS.

    :param geometry: The geometry to project (in WGS84)
    :param utm_crs: Optional UTM CRS to use. If None, estimate_utm_crs will be used
    :return: A tuple of (projected geometry, utm_crs)
    :raises ValueError: If the geometry cannot be projected
    """
    try:
        # Create a GeoDataFrame with the geometry
        gdf = gpd.GeoDataFrame(geometry=[geometry], crs="EPSG:4326")

        # If no UTM CRS is provided, estimate one based on the geometry's centroid
        if utm_crs is None:
            utm_crs = gdf.estimate_utm_crs()
            logger.debug(f"Estimated UTM CRS: {utm_crs}")
        # If utm_crs is a string, convert it to a pyproj.CRS object
        elif isinstance(utm_crs, str):
            utm_crs = pyproj.CRS(utm_crs)
            logger.debug(f"Converted string CRS to pyproj.CRS: {utm_crs}")

        # Project to the UTM CRS
        gdf_utm = gdf.to_crs(utm_crs)

        # Return the projected geometry and the UTM CRS
        # Use cast to ensure the type checker knows we're returning a GeometryType
        return cast(GeometryType, gdf_utm.geometry.iloc[0]), utm_crs
    except Exception as e:
        logger.error(f"Error projecting geometry to UTM: {e}")
        raise ValueError(f"Failed to project geometry to UTM: {e}")


def _project_to_wgs84(geometry: GeometryType, from_crs: Union[str, pyproj.CRS]) -> GeometryType:
    """
    Project a geometry from a specified CRS back to WGS84.

    :param geometry: The geometry to project
    :param from_crs: The CRS of the input geometry
    :return: The geometry projected to WGS84
    :raises ValueError: If the geometry cannot be projected
    """

    if geometry is None:
        raise ValueError("Geometry can not be None")

    try:
        # Create a GeoDataFrame with the geometry
        gdf = gpd.GeoDataFrame(geometry=[geometry], crs=from_crs)

        # Project to WGS84
        gdf_wgs84 = gdf.to_crs("EPSG:4326")

        # Return the projected geometry
        # Use cast to ensure the type checker knows we're returning a GeometryType
        return cast(GeometryType, gdf_wgs84.geometry.iloc[0])
    except Exception as e:
        logger.error(f"Error projecting geometry to WGS84: {e}")
        raise ValueError(f"Failed to project geometry to WGS84: {e}")


def _calculate_xy_offset(distance_meters: float, heading_degrees: float) -> Tuple[float, float]:
    """
    Calculate x and y offsets based on distance and heading.

    :param distance_meters: Distance in meters
    :param heading_degrees: Heading in degrees (0 = North, 90 = East, etc.)
    :return: A tuple of (x_offset, y_offset) in meters
    """
    # Convert heading from compass bearing (0 = North) to mathematical angle (0 = East)
    # Mathematical angle increases counterclockwise, compass bearing increases clockwise
    math_angle_rad = math.radians(90 - heading_degrees)

    # Calculate offsets using trigonometry
    x_offset = distance_meters * math.cos(math_angle_rad)
    y_offset = distance_meters * math.sin(math_angle_rad)

    return x_offset, y_offset


def buffer_geometry(geometry: GeometryType, buffer_distance_meters: float) -> GeometryType:
    """
    Buffer a geometry by a specified distance in meters.

    The input geometry is assumed to be in WGS84 (EPSG:4326) coordinates.
    The function projects the geometry to an appropriate UTM CRS, applies the buffer,
    and then projects back to WGS84.

    :param geometry: The geometry to buffer (in WGS84)
    :param buffer_distance_meters: Buffer distance in meters
    :return: The buffered geometry (in WGS84)
    :raises ValueError: If the geometry cannot be buffered
    """
    try:
        # Project to UTM
        utm_geometry, utm_crs = _project_to_utm(geometry)

        # Apply buffer
        buffered_geometry = utm_geometry.buffer(buffer_distance_meters)

        # Project back to WGS84
        wgs84_buffered_geometry = _project_to_wgs84(buffered_geometry, utm_crs)

        return wgs84_buffered_geometry
    except Exception as e:
        logger.error(f"Error buffering geometry: {e}")
        raise ValueError(f"Failed to buffer geometry: {e}")


def translate_geometry(geometry: GeometryType, distance_meters: float, heading_degrees: float) -> GeometryType:
    """
    Translate a geometry by a specified distance and heading.

    The input geometry is assumed to be in WGS84 (EPSG:4326) coordinates.
    The function projects the geometry to an appropriate UTM CRS, applies the translation,
    and then projects back to WGS84.

    :param geometry: The geometry to translate (in WGS84)
    :param distance_meters: Distance to translate in meters
    :param heading_degrees: Heading in degrees (0 = North, 90 = East, etc.)
    :return: The translated geometry (in WGS84)
    :raises ValueError: If the geometry cannot be translated
    """
    try:
        # Project to UTM
        utm_geometry, utm_crs = _project_to_utm(geometry)

        # Calculate x and y offsets
        x_offset, y_offset = _calculate_xy_offset(distance_meters, heading_degrees)

        # Apply translation
        translated_geometry = translate(utm_geometry, xoff=x_offset, yoff=y_offset)

        # Project back to WGS84
        wgs84_translated_geometry = _project_to_wgs84(translated_geometry, utm_crs)

        return wgs84_translated_geometry
    except Exception as e:
        logger.error(f"Error translating geometry: {e}")
        raise ValueError(f"Failed to translate geometry: {e}")
