#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
import math
import unittest

import geopandas as gpd
import pyproj
from shapely.geometry import LineString, Point, Polygon

from aws.osml.geoagents.spatial.spatial_transforms import (
    _calculate_xy_offset,
    _project_to_utm,
    _project_to_wgs84,
    buffer_geometry,
    translate_geometry,
)

# Set up logger
logger = logging.getLogger(__name__)


class TestSpatialTransforms(unittest.TestCase):
    """
    Test cases for spatial transformation functions.
    """

    def setUp(self) -> None:
        """
        Set up test fixtures with sample geometries.

        :return: None
        """
        # Create sample geometries in WGS84 (EPSG:4326)
        self.point = Point(-73.985428, 40.748817)  # NYC
        self.linestring = LineString([(-73.985428, 40.748817), (-73.988, 40.75)])  # Line in NYC
        self.polygon = Polygon(
            [(-73.985428, 40.748817), (-73.988, 40.748817), (-73.988, 40.75), (-73.985428, 40.75), (-73.985428, 40.748817)]
        )  # Polygon in NYC

        # Define a known UTM CRS for the test area (NYC is in UTM zone 18N)
        self.utm_crs = pyproj.CRS("EPSG:32618")  # UTM Zone 18N

    def test_project_to_utm_point(self) -> None:
        """
        Test projecting a Point from WGS84 to UTM.

        :return: None
        """
        # Project point to UTM
        utm_point, utm_crs = _project_to_utm(self.point)

        # Verify the result
        self.assertIsInstance(utm_point, Point)
        self.assertIsInstance(utm_crs, pyproj.CRS)

        # Check that the geometries are not identical (coordinates should change after projection)
        self.assertNotEqual(self.point.wkt, utm_point.wkt)

        # Verify the CRS is a UTM projection
        self.assertTrue("UTM" in utm_crs.name)

    def test_project_to_utm_linestring(self) -> None:
        """
        Test projecting a LineString from WGS84 to UTM.

        :return: None
        """
        # Project linestring to UTM
        utm_linestring, utm_crs = _project_to_utm(self.linestring)

        # Verify the result
        self.assertIsInstance(utm_linestring, LineString)
        self.assertIsInstance(utm_crs, pyproj.CRS)

        # Check that the geometries are not identical (coordinates should change after projection)
        self.assertNotEqual(self.linestring.wkt, utm_linestring.wkt)

        # Verify the CRS is a UTM projection
        self.assertTrue("UTM" in utm_crs.name)

    def test_project_to_utm_polygon(self) -> None:
        """
        Test projecting a Polygon from WGS84 to UTM.

        :return: None
        """
        # Project polygon to UTM
        utm_polygon, utm_crs = _project_to_utm(self.polygon)

        # Verify the result
        self.assertIsInstance(utm_polygon, Polygon)
        self.assertIsInstance(utm_crs, pyproj.CRS)

        # Check that the geometries are not identical (coordinates should change after projection)
        self.assertNotEqual(self.polygon.wkt, utm_polygon.wkt)

        # Verify the CRS is a UTM projection
        self.assertTrue("UTM" in utm_crs.name)

    def test_project_to_utm_with_custom_crs(self) -> None:
        """
        Test projecting a geometry with a custom UTM CRS.

        :return: None
        """
        # Project point to a specific UTM CRS
        utm_point, utm_crs = _project_to_utm(self.point, utm_crs=self.utm_crs)

        # Verify the result
        self.assertIsInstance(utm_point, Point)
        self.assertEqual(utm_crs, self.utm_crs)

        # Check that the geometries are not identical (coordinates should change after projection)
        self.assertNotEqual(self.point.wkt, utm_point.wkt)

    def test_project_to_utm_with_crs_string(self) -> None:
        """
        Test projecting a geometry with a CRS provided as a string.

        :return: None
        """
        # Project point to a specific UTM CRS provided as a string
        utm_point, utm_crs = _project_to_utm(self.point, utm_crs="EPSG:32618")

        # Verify the result
        self.assertIsInstance(utm_point, Point)
        self.assertEqual(utm_crs.to_epsg(), 32618)

        # Check that the geometries are not identical (coordinates should change after projection)
        self.assertNotEqual(self.point.wkt, utm_point.wkt)

    def test_project_to_utm_error(self) -> None:
        """
        Test error handling in _project_to_utm.

        :return: None
        """
        # Create an invalid geometry (None)
        invalid_geometry = None

        # Attempt to project the invalid geometry
        with self.assertRaises(ValueError):
            _project_to_utm(invalid_geometry)

    def test_project_to_wgs84_point(self) -> None:
        """
        Test projecting a Point from UTM to WGS84.

        :return: None
        """
        # First project to UTM
        utm_point, utm_crs = _project_to_utm(self.point)

        # Then project back to WGS84
        wgs84_point = _project_to_wgs84(utm_point, utm_crs)

        # Verify the result
        self.assertIsInstance(wgs84_point, Point)

        # The point should be very close to the original point after round-trip projection
        self.assertAlmostEqual(wgs84_point.x, self.point.x, places=5)
        self.assertAlmostEqual(wgs84_point.y, self.point.y, places=5)

    def test_project_to_wgs84_linestring(self) -> None:
        """
        Test projecting a LineString from UTM to WGS84.

        :return: None
        """
        # First project to UTM
        utm_linestring, utm_crs = _project_to_utm(self.linestring)

        # Then project back to WGS84
        wgs84_linestring = _project_to_wgs84(utm_linestring, utm_crs)

        # Verify the result
        self.assertIsInstance(wgs84_linestring, LineString)

        # The linestring should be very close to the original after round-trip projection
        original_coords = list(self.linestring.coords)
        result_coords = list(wgs84_linestring.coords)

        self.assertEqual(len(original_coords), len(result_coords))

        for i in range(len(original_coords)):
            self.assertAlmostEqual(result_coords[i][0], original_coords[i][0], places=5)
            self.assertAlmostEqual(result_coords[i][1], original_coords[i][1], places=5)

    def test_project_to_wgs84_polygon(self) -> None:
        """
        Test projecting a Polygon from UTM to WGS84.

        :return: None
        """
        # First project to UTM
        utm_polygon, utm_crs = _project_to_utm(self.polygon)

        # Then project back to WGS84
        wgs84_polygon = _project_to_wgs84(utm_polygon, utm_crs)

        # Verify the result
        self.assertIsInstance(wgs84_polygon, Polygon)

        # The polygon should be very close to the original after round-trip projection
        original_coords = list(self.polygon.exterior.coords)
        result_coords = list(wgs84_polygon.exterior.coords)

        self.assertEqual(len(original_coords), len(result_coords))

        for i in range(len(original_coords)):
            self.assertAlmostEqual(result_coords[i][0], original_coords[i][0], places=5)
            self.assertAlmostEqual(result_coords[i][1], original_coords[i][1], places=5)

    def test_project_to_wgs84_error(self) -> None:
        """
        Test error handling in _project_to_wgs84.

        :return: None
        """
        # Create an invalid geometry (None)
        invalid_geometry = None

        # Attempt to project the invalid geometry
        with self.assertRaises(ValueError):
            _project_to_wgs84(invalid_geometry, self.utm_crs)

    def test_calculate_xy_offset(self) -> None:
        """
        Test calculating x and y offsets based on distance and heading.

        :return: None
        """
        # Test cases with known results
        test_cases = [
            # (distance, heading, expected_x, expected_y)
            (100, 0, 0, 100),  # North
            (100, 90, 100, 0),  # East
            (100, 180, 0, -100),  # South
            (100, 270, -100, 0),  # West
            (100, 45, 70.71, 70.71),  # Northeast (approximately)
        ]

        for distance, heading, expected_x, expected_y in test_cases:
            x_offset, y_offset = _calculate_xy_offset(distance, heading)

            # Check that the offsets are close to the expected values
            self.assertAlmostEqual(x_offset, expected_x, delta=0.1)
            self.assertAlmostEqual(y_offset, expected_y, delta=0.1)

    def test_buffer_geometry_point(self) -> None:
        """
        Test buffering a Point geometry.

        :return: None
        """
        # Buffer the point by 100 meters
        buffer_distance = 100
        buffered_point = buffer_geometry(self.point, buffer_distance)

        # Verify the result
        self.assertIsInstance(buffered_point, Polygon)

        # The buffered point should be a circle around the original point
        # Project both geometries to UTM for accurate area calculation
        utm_point, utm_crs = _project_to_utm(self.point)
        utm_buffered_point = _project_to_wgs84(buffered_point, "EPSG:4326")
        utm_buffered_point = (
            gpd.GeoDataFrame(geometry=[utm_buffered_point], crs="EPSG:4326").to_crs(utm_crs).geometry.iloc[0]
        )

        # Calculate the expected area (πr²)
        expected_area = math.pi * buffer_distance * buffer_distance

        # Check that the area is close to the expected value
        self.assertAlmostEqual(utm_buffered_point.area, expected_area, delta=expected_area * 0.1)

    def test_buffer_geometry_linestring(self) -> None:
        """
        Test buffering a LineString geometry.

        :return: None
        """
        # Buffer the linestring by 50 meters
        buffer_distance = 50
        buffered_linestring = buffer_geometry(self.linestring, buffer_distance)

        # Verify the result
        self.assertIsInstance(buffered_linestring, Polygon)

        # The buffered linestring should contain the original linestring
        self.assertTrue(buffered_linestring.contains(self.linestring))

        # Project to UTM for accurate measurements
        utm_linestring, utm_crs = _project_to_utm(self.linestring)
        utm_buffered_linestring = _project_to_wgs84(buffered_linestring, "EPSG:4326")
        utm_buffered_linestring = (
            gpd.GeoDataFrame(geometry=[utm_buffered_linestring], crs="EPSG:4326").to_crs(utm_crs).geometry.iloc[0]
        )

        # Check that the buffer distance is approximately correct
        # by measuring the distance from the linestring to the buffer boundary
        # This is a simplification - we just check one point
        point_on_linestring = utm_linestring.interpolate(0.5, normalized=True)
        distance_to_boundary = utm_buffered_linestring.boundary.distance(point_on_linestring)

        self.assertAlmostEqual(distance_to_boundary, buffer_distance, delta=buffer_distance * 0.1)

    def test_buffer_geometry_polygon(self) -> None:
        """
        Test buffering a Polygon geometry.

        :return: None
        """
        # Buffer the polygon by 75 meters
        buffer_distance = 75
        buffered_polygon = buffer_geometry(self.polygon, buffer_distance)

        # Verify the result
        self.assertIsInstance(buffered_polygon, Polygon)

        # The buffered polygon should contain the original polygon
        self.assertTrue(buffered_polygon.contains(self.polygon))

        # Project to UTM for accurate measurements
        utm_polygon, utm_crs = _project_to_utm(self.polygon)
        utm_buffered_polygon = _project_to_wgs84(buffered_polygon, "EPSG:4326")
        utm_buffered_polygon = (
            gpd.GeoDataFrame(geometry=[utm_buffered_polygon], crs="EPSG:4326").to_crs(utm_crs).geometry.iloc[0]
        )

        # Check that the buffer distance is approximately correct
        # by measuring the distance from the polygon boundary to the buffer boundary
        # This is a simplification - we just check one point
        point_on_boundary = utm_polygon.boundary.interpolate(0.5, normalized=True)
        distance_to_buffer_boundary = utm_buffered_polygon.boundary.distance(point_on_boundary)

        self.assertAlmostEqual(distance_to_buffer_boundary, buffer_distance, delta=buffer_distance * 0.1)

    def test_buffer_geometry_error(self) -> None:
        """
        Test error handling in buffer_geometry.

        :return: None
        """
        # Create an invalid geometry (None)
        invalid_geometry = None

        # Attempt to buffer the invalid geometry
        with self.assertRaises(ValueError):
            buffer_geometry(invalid_geometry, 100)

    def test_translate_geometry_point(self) -> None:
        """
        Test translating a Point geometry.

        :return: None
        """
        # Translate the point 200 meters east
        distance = 200
        heading = 90  # East
        translated_point = translate_geometry(self.point, distance, heading)

        # Verify the result
        self.assertIsInstance(translated_point, Point)

        # Project both points to UTM for accurate distance calculation
        utm_point, utm_crs = _project_to_utm(self.point)
        utm_translated_point = _project_to_wgs84(translated_point, "EPSG:4326")
        utm_translated_point = (
            gpd.GeoDataFrame(geometry=[utm_translated_point], crs="EPSG:4326").to_crs(utm_crs).geometry.iloc[0]
        )

        # Calculate the distance between the original and translated points
        actual_distance = utm_point.distance(utm_translated_point)

        # Check that the distance is close to the expected value
        self.assertAlmostEqual(actual_distance, distance, delta=distance * 0.1)

    def test_translate_geometry_linestring(self) -> None:
        """
        Test translating a LineString geometry.

        :return: None
        """
        # Translate the linestring 150 meters north
        distance = 150
        heading = 0  # North
        translated_linestring = translate_geometry(self.linestring, distance, heading)

        # Verify the result
        self.assertIsInstance(translated_linestring, LineString)

        # Project both linestrings to UTM for accurate distance calculation
        utm_linestring, utm_crs = _project_to_utm(self.linestring)
        utm_translated_linestring = _project_to_wgs84(translated_linestring, "EPSG:4326")
        utm_translated_linestring = (
            gpd.GeoDataFrame(geometry=[utm_translated_linestring], crs="EPSG:4326").to_crs(utm_crs).geometry.iloc[0]
        )

        # Calculate the distance between the centroids of the original and translated linestrings
        actual_distance = utm_linestring.centroid.distance(utm_translated_linestring.centroid)

        # Check that the distance is close to the expected value
        self.assertAlmostEqual(actual_distance, distance, delta=distance * 0.1)

    def test_translate_geometry_polygon(self) -> None:
        """
        Test translating a Polygon geometry.

        :return: None
        """
        # Translate the polygon 250 meters southwest
        distance = 250
        heading = 225  # Southwest
        translated_polygon = translate_geometry(self.polygon, distance, heading)

        # Verify the result
        self.assertIsInstance(translated_polygon, Polygon)

        # Project both polygons to UTM for accurate distance calculation
        utm_polygon, utm_crs = _project_to_utm(self.polygon)
        utm_translated_polygon = _project_to_wgs84(translated_polygon, "EPSG:4326")
        utm_translated_polygon = (
            gpd.GeoDataFrame(geometry=[utm_translated_polygon], crs="EPSG:4326").to_crs(utm_crs).geometry.iloc[0]
        )

        # Calculate the distance between the centroids of the original and translated polygons
        actual_distance = utm_polygon.centroid.distance(utm_translated_polygon.centroid)

        # Check that the distance is close to the expected value
        self.assertAlmostEqual(actual_distance, distance, delta=distance * 0.1)

    def test_translate_geometry_error(self) -> None:
        """
        Test error handling in translate_geometry.

        :return: None
        """
        # Create an invalid geometry (None)
        invalid_geometry = None

        # Attempt to translate the invalid geometry
        with self.assertRaises(ValueError):
            translate_geometry(invalid_geometry, 100, 90)


if __name__ == "__main__":
    unittest.main()
