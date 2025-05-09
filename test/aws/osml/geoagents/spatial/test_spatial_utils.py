#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import geopandas as gpd
from pystac import Item
from shapely.geometry import Point

from aws.osml.geoagents.common import Georeference, ToolExecutionError, Workspace
from aws.osml.geoagents.spatial.spatial_utils import (
    create_derived_stac_item,
    download_georef_from_workspace,
    is_parquet_file,
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

    @patch("geopandas.read_parquet")
    def test_read_geo_data_frame_parquet(self, mock_read_parquet):
        mock_read_parquet.return_value = self.sample_gdf

        with patch("aws.osml.geoagents.spatial.spatial_utils.is_parquet_file", return_value=True):
            result = read_geo_data_frame(Path("test.parquet"))
            self.assertIsInstance(result, gpd.GeoDataFrame)
            mock_read_parquet.assert_called_once()

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
            with self.assertRaises(ToolExecutionError):
                read_geo_data_frame(Path("test.parquet"))

    def test_write_geo_data_frame(self):
        test_path = Path("test/output.parquet")

        with patch("pathlib.Path.mkdir") as mock_mkdir:
            with patch.object(self.sample_gdf, "to_parquet") as mock_to_parquet:
                write_geo_data_frame(test_path, self.sample_gdf)

                mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
                mock_to_parquet.assert_called_once_with(test_path)

    def test_download_georef_from_workspace(self):
        # Create mock workspace and georeference
        mock_workspace = Mock(spec=Workspace)
        mock_georef = Mock(spec=Georeference)
        mock_georef.asset_tag = "test_asset"

        # Create mock STAC item
        mock_item = Mock(spec=Item)
        mock_assets = {"test_asset": Path("test/path")}

        # Configure workspace mock
        mock_workspace.get_item.return_value = mock_item
        mock_workspace.download_assets.return_value = mock_assets

        # Test successful download
        item, assets = download_georef_from_workspace(mock_georef, mock_workspace)

        self.assertEqual(item, mock_item)
        self.assertEqual(assets, mock_assets)
        mock_workspace.get_item.assert_called_once_with(mock_georef)
        mock_workspace.download_assets.assert_called_once_with(mock_item, ["test_asset"])

    def test_download_georef_from_workspace_error(self):
        mock_workspace = Mock(spec=Workspace)
        mock_georef = Mock(spec=Georeference)
        mock_workspace.get_item.side_effect = Exception("Download error")

        with self.assertRaises(ToolExecutionError):
            download_georef_from_workspace(mock_georef, mock_workspace)

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


if __name__ == "__main__":
    unittest.main()
