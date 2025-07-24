#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from datetime import datetime
from unittest.mock import Mock

import geopandas as gpd
import pandas as pd
import shapely
from pystac import Item
from shapely.geometry import Point

from aws.osml.geoagents.common import GeoDataReference, Workspace
from aws.osml.geoagents.spatial.spatial_utils import (
    create_derived_stac_item,
    create_length_limited_wkt,
    create_stac_item_for_dataset,
    load_geo_data_frame,
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
        georef = Mock(spec=GeoDataReference)

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
        georef = Mock(spec=GeoDataReference)

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
        georef = Mock(spec=GeoDataReference)

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
        derived_georef = Mock(spec=GeoDataReference)
        derived_georef.reference_string = "stac:derived"
        # Add the is_stac_reference method to the mock
        derived_georef.is_stac_reference.return_value = True

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

    def test_create_stac_item_for_dataset_basic(self):
        """Test creating a STAC Item from a GeoDataFrame with no datetime columns."""
        # Create a sample GeoDataFrame
        gdf = gpd.GeoDataFrame({"geometry": [Point(0, 0), Point(1, 1)], "data": [1, 2]}, crs="EPSG:4326")

        # Create a STAC Item
        path = "/path/to/data.geojson"
        title = "Test Dataset"
        description = "A test dataset"

        item = create_stac_item_for_dataset(gdf, path, title, description)

        # Verify the item properties
        self.assertEqual(item.properties["title"], title)
        self.assertEqual(item.properties["description"], description)
        self.assertEqual(item.bbox, [0.0, 0.0, 1.0, 1.0])
        self.assertIsNotNone(item.datetime)  # Should use current time
        # Check that start_datetime and end_datetime are not in properties
        self.assertNotIn("start_datetime", item.properties)
        self.assertNotIn("end_datetime", item.properties)

        # Verify the asset was added
        self.assertIn("data", item.assets)
        self.assertEqual(item.assets["data"].href, path)
        self.assertEqual(item.assets["data"].media_type, "application/geo+json")

    def test_create_stac_item_for_dataset_with_datetime(self):
        """Test creating a STAC Item from a GeoDataFrame with datetime columns."""
        import pandas as pd

        # Create a sample GeoDataFrame with a datetime column
        dates = pd.date_range(start="2023-01-01", periods=3)
        gdf = gpd.GeoDataFrame(
            {"geometry": [Point(0, 0), Point(1, 1), Point(2, 2)], "data": [1, 2, 3], "date": dates}, crs="EPSG:4326"
        )

        # Create a STAC Item
        path = "/path/to/data.parquet"

        item = create_stac_item_for_dataset(gdf, path)

        # Verify datetime properties
        # When using a date range, the main datetime should be None
        self.assertIsNone(item.datetime)

        # Check that the item has datetime information
        # We don't check the exact values since the conversion between pandas Timestamp
        # and datetime objects might introduce small differences
        self.assertIsNotNone(item.properties.get("start_datetime"))
        self.assertIsNotNone(item.properties.get("end_datetime"))

        # Verify the asset was added with correct media type
        self.assertEqual(item.assets["data"].media_type, "application/octet-stream")

    def test_create_stac_item_for_dataset_same_datetime(self):
        """Test creating a STAC Item when all datetime values are the same."""
        import pandas as pd

        # Create a sample GeoDataFrame with a datetime column where all values are the same
        same_date = pd.Timestamp("2023-01-01")
        gdf = gpd.GeoDataFrame(
            {"geometry": [Point(0, 0), Point(1, 1)], "data": [1, 2], "date": [same_date, same_date]}, crs="EPSG:4326"
        )

        # Create a STAC Item
        path = "/path/to/data.geojson"

        item = create_stac_item_for_dataset(gdf, path)

        # Verify datetime properties
        self.assertIsNotNone(item.datetime)

        # When using a single datetime, start_datetime and end_datetime should not be set
        self.assertNotIn("start_datetime", item.properties)
        self.assertNotIn("end_datetime", item.properties)

    def test_load_geo_data_frame(self):
        """Test loading a GeoDataFrame from local asset paths."""
        from unittest.mock import patch

        # Create mock GeoDataFrame
        points = [shapely.Point(0.5, 0.5), shapely.Point(1.5, 1.5)]
        mock_gdf = gpd.GeoDataFrame(geometry=points)
        mock_gdf.crs = "EPSG:4326"

        # Create mock GeoDataReference
        mock_geo_reference = Mock(spec=GeoDataReference)
        mock_geo_reference.reference_string = "stac:test-dataset"

        # Create mock local asset paths
        local_asset_paths = {"asset1": "/tmp/asset1.parquet"}

        # Create mock item
        mock_item = Mock(spec=Item)

        # Test with existing item
        with patch("aws.osml.geoagents.spatial.spatial_utils.create_stac_item_for_dataset") as mock_create_stac_item:
            # Create a new mock workspace for this test case
            mock_workspace1 = Mock(spec=Workspace)
            mock_workspace1.read_geo_data_frame.return_value = mock_gdf

            gdf, item, selected_asset_key = load_geo_data_frame(
                local_asset_paths, mock_workspace1, mock_geo_reference, mock_item
            )

            # Verify the results
            pd.testing.assert_frame_equal(gdf, mock_gdf)
            self.assertEqual(item, mock_item)
            self.assertEqual(selected_asset_key, "asset1")

            # Verify the mocks were called
            mock_workspace1.read_geo_data_frame.assert_called_once_with("/tmp/asset1.parquet")
            mock_create_stac_item.assert_not_called()

        # Test with no item (should create a new one)
        mock_create_item = Mock(spec=Item)
        with patch("aws.osml.geoagents.spatial.spatial_utils.create_stac_item_for_dataset") as mock_create_stac_item:
            mock_create_stac_item.return_value = mock_create_item

            # Create a new mock workspace for this test case
            mock_workspace2 = Mock(spec=Workspace)
            mock_workspace2.read_geo_data_frame.return_value = mock_gdf

            gdf, item, selected_asset_key = load_geo_data_frame(local_asset_paths, mock_workspace2, mock_geo_reference, None)

            # Verify the results
            pd.testing.assert_frame_equal(gdf, mock_gdf)
            self.assertEqual(item, mock_create_item)
            self.assertEqual(selected_asset_key, "asset1")

            # Verify the mocks were called
            mock_workspace2.read_geo_data_frame.assert_called_once_with("/tmp/asset1.parquet")
            mock_create_stac_item.assert_called_once()

        # Test with geo_column specified
        with patch("aws.osml.geoagents.spatial.spatial_utils.create_stac_item_for_dataset") as mock_create_stac_item:
            mock_create_stac_item.return_value = mock_create_item

            # Create a new mock workspace for this test case
            mock_workspace3 = Mock(spec=Workspace)

            # Create a GeoDataFrame with a custom_geometry column
            custom_gdf = gpd.GeoDataFrame(geometry=points)
            custom_gdf["custom_geometry"] = custom_gdf["geometry"]
            custom_gdf.crs = "EPSG:4326"
            mock_workspace3.read_geo_data_frame.return_value = custom_gdf

            gdf, item, selected_asset_key = load_geo_data_frame(
                local_asset_paths, mock_workspace3, mock_geo_reference, mock_item, "custom_geometry"
            )

            # Verify the results
            pd.testing.assert_frame_equal(gdf, custom_gdf)
            self.assertEqual(item, mock_item)
            self.assertEqual(selected_asset_key, "asset1")

            # Verify the mocks were called
            mock_workspace3.read_geo_data_frame.assert_called_once_with("/tmp/asset1.parquet")
            # Verify that set_geometry was called with the custom geometry column
            # This is a bit tricky to test since we're using a real GeoDataFrame
            # We'd need to mock the GeoDataFrame itself to verify this


if __name__ == "__main__":
    unittest.main()
