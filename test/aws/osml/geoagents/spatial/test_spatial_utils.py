#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from datetime import datetime
from unittest.mock import Mock

import geopandas as gpd
import shapely
from pystac import Item
from shapely.geometry import Point

from aws.osml.geoagents.common import Georeference
from aws.osml.geoagents.spatial.spatial_utils import (
    create_derived_stac_item,
    create_length_limited_wkt,
    validate_dataset_crs,
)


class TestSpatialUtils(unittest.TestCase):
    def setUp(self):
        # Create sample GeoDataFrame for testing
        self.sample_gdf = gpd.GeoDataFrame({"geometry": [Point(0, 0), Point(1, 1)], "data": [1, 2]})

    def test_validate_dataset_crs_none(self):
        """Test validating a dataset with no CRS."""
        # Create a GeoDataFrame with no CRS
        gdf = self.sample_gdf.copy()
        gdf.crs = None

        # Create a mock georeference
        georef = Mock(spec=Georeference)

        # Call the function
        validate_dataset_crs(gdf, georef)

        # Check that the CRS was set to EPSG:4326
        self.assertEqual(gdf.crs, "EPSG:4326")

    def test_validate_dataset_crs_valid(self):
        """Test validating a dataset with a valid CRS."""
        # Create a GeoDataFrame with EPSG:4326 CRS
        gdf = self.sample_gdf.copy()
        gdf.set_crs("EPSG:4326", inplace=True)

        # Create a mock georeference
        georef = Mock(spec=Georeference)

        # Call the function
        validate_dataset_crs(gdf, georef)

        # Check that the CRS is still EPSG:4326
        self.assertEqual(gdf.crs, "EPSG:4326")

    def test_validate_dataset_crs_invalid(self):
        """Test validating a dataset with an invalid CRS."""
        # Create a GeoDataFrame with a different CRS
        gdf = self.sample_gdf.copy()
        gdf.set_crs("EPSG:3857", inplace=True)

        # Create a mock georeference
        georef = Mock(spec=Georeference)

        # Call the function and check that it raises a ValueError
        with self.assertRaises(ValueError):
            validate_dataset_crs(gdf, georef)

    def test_create_derived_stac_item(self):
        # Create mock original item
        original_item = Item(
            id="original",
            geometry={"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
            bbox=[0, 0, 1, 1],
            datetime=datetime.now(),
            properties={
                "start_datetime": "2023-01-01T00:00:00Z",
                "end_datetime": "2023-01-02T00:00:00Z",
                "title": "Original Dataset",
                "keywords": ["test"],
            },
        )

        # Create test georeference
        derived_georef = Mock(spec=Georeference)
        derived_georef.item_id = "derived"

        # Test creation of derived item
        derived_item = create_derived_stac_item(
            derived_georef, "Derived Dataset Title", "Derived dataset description", original_item
        )

        self.assertEqual(derived_item.id, "derived")
        self.assertEqual(derived_item.geometry, original_item.geometry)
        self.assertEqual(derived_item.bbox, original_item.bbox)
        self.assertEqual(derived_item.properties["title"], "Derived Dataset Title")
        self.assertEqual(derived_item.properties["keywords"], ["test"])
        self.assertEqual(derived_item.properties["description"], "Derived dataset description")

    def test_create_length_limited_wkt_basic(self):
        """Test that the function returns a WKT string under the specified length."""
        # Create a complex polygon by buffering a point
        point = Point(-77.0, 38.9)
        complex_geometry = point.buffer(0.01, quad_segs=32)

        # Get original WKT length
        original_wkt = shapely.to_wkt(complex_geometry)
        original_length = len(original_wkt)

        # Test with a limit larger than the original
        max_length = original_length + 100
        limited_wkt = create_length_limited_wkt(complex_geometry, max_length)
        self.assertLessEqual(len(limited_wkt), max_length)

        # Test with a smaller limit
        max_length = original_length // 2
        limited_wkt = create_length_limited_wkt(complex_geometry, max_length)
        self.assertLessEqual(len(limited_wkt), max_length)

    def test_create_length_limited_wkt_simplification(self):
        """Test that the function applies simplification when needed."""
        # Create a very complex polygon with many points
        complex_polygon = Point(-77.0, 38.9).buffer(0.01, quad_segs=64)

        # Get original point count by counting coordinate pairs in WKT
        original_wkt = shapely.to_wkt(complex_polygon)

        # Set a very small limit that will require significant simplification
        very_small_limit = 200
        limited_wkt = create_length_limited_wkt(complex_polygon, very_small_limit)

        # Verify the result is under the limit
        self.assertLessEqual(len(limited_wkt), very_small_limit)

        # Verify the simplified geometry has fewer points
        self.assertLess(len(limited_wkt), len(original_wkt))

    def test_create_length_limited_wkt_error(self):
        """Test that the function raises ValueError when it can't meet the requirement."""
        # Create a complex polygon
        complex_polygon = Point(-77.0, 38.9).buffer(0.01, quad_segs=32)

        # Try with an impossibly small limit
        with self.assertRaises(ValueError):
            create_length_limited_wkt(complex_polygon, 5)


if __name__ == "__main__":
    unittest.main()
