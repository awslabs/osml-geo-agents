#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import geopandas as gpd
import shapely
from pystac import Item
from shapely.geometry import Point

from aws.osml.geoagents.common import Georeference
from aws.osml.geoagents.spatial.spatial_utils import (
    create_derived_stac_item,
    create_length_limited_wkt,
    is_parquet_file,
    read_field_descriptions_from_parquet,
    read_geo_data_frame,
    write_geo_data_frame,
)


class TestSpatialUtils(unittest.TestCase):
    def setUp(self):
        # Create sample GeoDataFrame for testing
        self.sample_gdf = gpd.GeoDataFrame({"geometry": [Point(0, 0), Point(1, 1)], "data": [1, 2]})

    def test_is_parquet_file_true(self):
        # Test with valid Parquet file
        with patch("builtins.open", mock_open(read_data=b"PAR1")):
            result = is_parquet_file(Path("test.parquet"))
            self.assertTrue(result)

    def test_is_parquet_file_false(self):
        # Test with non-Parquet file
        with patch("builtins.open", mock_open(read_data=b"NOT1")):
            result = is_parquet_file(Path("test.txt"))
            self.assertFalse(result)

    def test_is_parquet_file_error(self):
        # Test with file open error
        with patch("builtins.open", side_effect=Exception):
            result = is_parquet_file(Path("nonexistent.parquet"))
            self.assertFalse(result)

    @patch("pyarrow.parquet.read_table")
    def test_read_field_descriptions_from_parquet(self, mock_read_table):
        # Mock the schema with field metadata
        mock_schema = Mock()
        mock_field = Mock()
        mock_field.metadata = {b"comment": b"Test description"}
        mock_schema.names = ["test_field"]
        mock_schema.field.return_value = mock_field
        mock_read_table.return_value.schema = mock_schema

        result = read_field_descriptions_from_parquet(Path("test.parquet"))

        self.assertEqual(result, {"test_field": "Test description"})
        mock_read_table.assert_called_once()
        mock_schema.field.assert_called_once_with("test_field")

    @patch("geopandas.read_parquet")
    @patch("aws.osml.geoagents.spatial.spatial_utils.read_field_descriptions_from_parquet")
    def test_read_geo_data_frame_parquet(self, mock_read_descriptions, mock_read_parquet):
        # Create sample GeoDataFrame with column descriptions
        sample_gdf = self.sample_gdf.copy()
        column_descriptions = {"data": "Test column description"}

        mock_read_parquet.return_value = sample_gdf
        mock_read_descriptions.return_value = column_descriptions

        with patch("aws.osml.geoagents.spatial.spatial_utils.is_parquet_file", return_value=True):
            result = read_geo_data_frame(Path("test.parquet"))

            self.assertIsInstance(result, gpd.GeoDataFrame)
            self.assertEqual(result.attrs.get("column-descriptions"), column_descriptions)
            mock_read_parquet.assert_called_once()
            mock_read_descriptions.assert_called_once()

    @patch("geopandas.GeoDataFrame.from_file")
    def test_read_geo_data_frame_non_parquet(self, mock_from_file):
        mock_from_file.return_value = self.sample_gdf

        with patch("aws.osml.geoagents.spatial.spatial_utils.is_parquet_file", return_value=False):
            result = read_geo_data_frame(Path("test.shp"))
            self.assertIsInstance(result, gpd.GeoDataFrame)
            mock_from_file.assert_called_once()

    @patch("geopandas.read_parquet")
    def test_read_geo_data_frame_error(self, mock_read_parquet):
        mock_read_parquet.side_effect = Exception("Read error")

        with patch("aws.osml.geoagents.spatial.spatial_utils.is_parquet_file", return_value=True):
            with self.assertRaises(ValueError):
                read_geo_data_frame(Path("test.parquet"))

    def test_write_geo_data_frame(self):
        test_path = Path("test/output.parquet")

        with patch("pathlib.Path.mkdir") as mock_mkdir:
            with patch.object(self.sample_gdf, "to_parquet") as mock_to_parquet:
                write_geo_data_frame(test_path, self.sample_gdf)

                mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
                mock_to_parquet.assert_called_once_with(test_path)

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
