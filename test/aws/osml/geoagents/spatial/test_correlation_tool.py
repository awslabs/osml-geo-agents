#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import geopandas as gpd
from pystac import Asset, Item
from shapely.geometry import Polygon

from aws.osml.geoagents.common import ToolExecutionError, Workspace
from aws.osml.geoagents.spatial.correlation_tool import CorrelationTool


class TestCorrelationTool(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.tool = CorrelationTool()
        self.mock_workspace = Mock(spec=Workspace)
        self.mock_workspace.session_local_path = Path("/tmp/osml-geo-agents/test")

        # Create sample event with required parameters
        self.event = {
            "actionGroup": "SpatialReasoning",
            "function": "CORRELATE",
            "parameters": [
                {"name": "dataset1", "value": "georef:dataset1", "type": "string"},
                {"name": "dataset2", "value": "georef:dataset2", "type": "string"},
                {"name": "correlation_type", "value": "intersection", "type": "string"},
                {"name": "distance", "value": "100", "type": "string"},
            ],
        }

        # Create sample STAC items
        self.sample_item1 = Item(
            id="dataset1",
            geometry={"type": "Polygon", "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]]},
            datetime=datetime.fromisoformat("2025-04-23T14:05:23Z"),
            bbox=[0, 0, 2, 2],
            properties={
                "title": "Test Dataset 1",
                "keywords": ["test"],
            },
            assets={"data": Asset(href="s3://fake-test-bucket/data1.parquet")},
        )

        self.sample_item2 = Item(
            id="dataset2",
            geometry={"type": "Polygon", "coordinates": [[[1, 1], [3, 1], [3, 3], [1, 3], [1, 1]]]},
            datetime=datetime.fromisoformat("2025-04-23T14:05:23Z"),
            bbox=[1, 1, 3, 3],
            properties={
                "title": "Test Dataset 2",
                "keywords": ["test"],
            },
            assets={"data": Asset(href="s3://fake-test-bucket/data2.parquet")},
        )

    def create_gdf1(self):
        """Helper to create first test GeoDataFrame"""
        polygons = [Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]), Polygon([(1, 0), (2, 0), (2, 1), (1, 1)])]
        data = {"geometry": polygons, "id": [1, 2], "name": ["Area A", "Area B"]}
        return gpd.GeoDataFrame(data)

    def create_gdf2(self):
        """Helper to create second test GeoDataFrame"""
        polygons = [
            Polygon([(0.5, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 1.5)]),
            Polygon([(1.5, 0.5), (2.5, 0.5), (2.5, 1.5), (1.5, 1.5)]),
        ]
        data = {"geometry": polygons, "id": [3, 4], "category": ["Type X", "Type Y"]}
        return gpd.GeoDataFrame(data)

    def test_init(self):
        """Test CorrelationTool initialization."""
        self.assertEqual(self.tool.action_group, "SpatialReasoning")
        self.assertEqual(self.tool.function_name, "CORRELATE")

    @patch("aws.osml.geoagents.spatial.correlation_tool.LocalAssets")
    @patch("aws.osml.geoagents.spatial.correlation_tool.read_geo_data_frame")
    @patch("aws.osml.geoagents.spatial.correlation_tool.write_geo_data_frame")
    @patch("aws.osml.geoagents.spatial.correlation_tool.create_derived_stac_item")
    def test_handler_with_geo_columns(self, mock_create_item, mock_write_gdf, mock_read_gdf, mock_local_assets):
        """Test correlation operation with geometry column names specified."""
        # Modify event to include geometry column parameters
        event_with_geo_columns = self.event.copy()
        event_with_geo_columns["parameters"].extend(
            [
                {"name": "dataset1_geo_column_name", "value": "geometry", "type": "string"},
                {"name": "dataset2_geo_column_name", "value": "geometry", "type": "string"},
            ]
        )

        # Setup LocalAssets mock
        mock_context1 = MagicMock()
        mock_context1.__enter__.return_value = (self.sample_item1, {"data": Path("/tmp/test/data1.parquet")})
        mock_context2 = MagicMock()
        mock_context2.__enter__.return_value = (self.sample_item2, {"data": Path("/tmp/test/data2.parquet")})
        mock_local_assets.side_effect = [mock_context1, mock_context2]

        gdf1 = self.create_gdf1()
        gdf2 = self.create_gdf2()
        mock_read_gdf.side_effect = [gdf1, gdf2]

        # Create a mock derived item
        mock_derived_item = Mock()
        mock_create_item.return_value = mock_derived_item

        # Execute handler
        result = self.tool.handler(event_with_geo_columns, {}, self.mock_workspace)

        # Verify response
        self.assertIn("The datasets georef:dataset1 and georef:dataset2 have been correlated", str(result))
        self.assertIn("intersection operation", str(result))

    @patch("aws.osml.geoagents.spatial.correlation_tool.LocalAssets")
    @patch("aws.osml.geoagents.spatial.correlation_tool.read_geo_data_frame")
    @patch("aws.osml.geoagents.spatial.correlation_tool.write_geo_data_frame")
    @patch("aws.osml.geoagents.spatial.correlation_tool.create_derived_stac_item")
    def test_handler_with_buffer(self, mock_create_item, mock_write_gdf, mock_read_gdf, mock_local_assets):
        """Test correlation operation with buffer applied."""
        # Setup LocalAssets mock
        mock_context1 = MagicMock()
        mock_context1.__enter__.return_value = (self.sample_item1, {"data": Path("/tmp/test/data1.parquet")})
        mock_context2 = MagicMock()
        mock_context2.__enter__.return_value = (self.sample_item2, {"data": Path("/tmp/test/data2.parquet")})
        mock_local_assets.side_effect = [mock_context1, mock_context2]

        gdf1 = self.create_gdf1()
        gdf2 = self.create_gdf2()
        mock_read_gdf.side_effect = [gdf1, gdf2]

        # Create a mock derived item
        mock_derived_item = Mock()
        mock_create_item.return_value = mock_derived_item

        # Execute handler
        result = self.tool.handler(self.event, {}, self.mock_workspace)

        # Verify buffer was mentioned in the response
        self.assertIn("buffer of 100", str(result).lower())

        # Verify method calls
        self.assertEqual(mock_local_assets.call_count, 2)
        self.assertEqual(mock_read_gdf.call_count, 2)
        mock_write_gdf.assert_called_once()
        mock_create_item.assert_called_once()
        self.mock_workspace.publish_item.assert_called_once()

    @patch("aws.osml.geoagents.spatial.correlation_tool.LocalAssets")
    @patch("aws.osml.geoagents.spatial.correlation_tool.read_geo_data_frame")
    @patch("aws.osml.geoagents.spatial.correlation_tool.write_geo_data_frame")
    @patch("aws.osml.geoagents.spatial.correlation_tool.create_derived_stac_item")
    def test_handler_with_invalid_geo_column(self, mock_create_item, mock_write_gdf, mock_read_gdf, mock_local_assets):
        """Test correlation operation with invalid geometry column name."""
        # Modify event to include an invalid geometry column parameter
        event_with_invalid_geo_column = self.event.copy()
        event_with_invalid_geo_column["parameters"].append(
            {"name": "dataset1_geo_column_name", "value": "nonexistent_column", "type": "string"}
        )

        # Setup LocalAssets mock
        mock_context1 = MagicMock()
        mock_context1.__enter__.return_value = (self.sample_item1, {"data": Path("/tmp/test/data1.parquet")})
        mock_context2 = MagicMock()
        mock_context2.__enter__.return_value = (self.sample_item2, {"data": Path("/tmp/test/data2.parquet")})
        mock_local_assets.side_effect = [mock_context1, mock_context2]

        gdf1 = self.create_gdf1()
        gdf2 = self.create_gdf2()
        mock_read_gdf.side_effect = [gdf1, gdf2]

        # Create a mock derived item
        mock_derived_item = Mock()
        mock_create_item.return_value = mock_derived_item

        # Execute handler and expect an error
        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(event_with_invalid_geo_column, {}, self.mock_workspace)

        self.assertIn("Unable to correlate the datasets", str(context.exception))

    def test_default_correlation_type(self):
        """Test that correlation_type defaults to intersection when not provided."""
        event_without_correlation_type = {
            "actionGroup": "SpatialReasoning",
            "function": "CORRELATE",
            "parameters": [
                {"name": "dataset1", "value": "georef:dataset1", "type": "string"},
                {"name": "dataset2", "value": "georef:dataset2", "type": "string"},
            ],
        }

        # Setup mocks for handler execution
        with patch("aws.osml.geoagents.spatial.correlation_tool.LocalAssets") as mock_local_assets, patch(
            "aws.osml.geoagents.spatial.correlation_tool.read_geo_data_frame"
        ) as mock_read_gdf, patch("aws.osml.geoagents.spatial.correlation_tool.write_geo_data_frame"), patch(
            "aws.osml.geoagents.spatial.correlation_tool.create_derived_stac_item"
        ):

            # Setup LocalAssets mock
            mock_context1 = MagicMock()
            mock_context1.__enter__.return_value = (self.sample_item1, {"data": Path("/tmp/test/data1.parquet")})
            mock_context2 = MagicMock()
            mock_context2.__enter__.return_value = (self.sample_item2, {"data": Path("/tmp/test/data2.parquet")})
            mock_local_assets.side_effect = [mock_context1, mock_context2]

            # Setup read_geo_data_frame mock
            gdf1 = self.create_gdf1()
            gdf2 = self.create_gdf2()
            mock_read_gdf.side_effect = [gdf1, gdf2]

            # Execute handler
            result = self.tool.handler(event_without_correlation_type, {}, self.mock_workspace)

            # Verify default correlation type was used
            self.assertIn("intersection operation", str(result))

    def test_missing_parameters(self):
        """Test handling of missing parameters."""
        # Test with missing dataset1
        missing_dataset1_event = {
            "actionGroup": "SpatialReasoning",
            "function": "CORRELATE",
            "parameters": [
                {"name": "dataset2", "value": "georef:dataset2", "type": "string"},
                {"name": "correlation_type", "value": "intersection", "type": "string"},
            ],
        }

        with self.assertRaises(ToolExecutionError):
            self.tool.handler(missing_dataset1_event, {}, self.mock_workspace)

        # Test with missing dataset2
        missing_dataset2_event = {
            "actionGroup": "SpatialReasoning",
            "function": "CORRELATE",
            "parameters": [
                {"name": "dataset1", "value": "georef:dataset1", "type": "string"},
                {"name": "correlation_type", "value": "intersection", "type": "string"},
            ],
        }

        with self.assertRaises(ToolExecutionError):
            self.tool.handler(missing_dataset2_event, {}, self.mock_workspace)

    @patch("aws.osml.geoagents.spatial.correlation_tool.LocalAssets")
    def test_workspace_download_error(self, mock_local_assets):
        """Test error handling when workspace download fails."""
        # Setup mock to raise exception
        mock_context = MagicMock()
        mock_context.__enter__.side_effect = Exception("Failed to download dataset")
        mock_local_assets.return_value = mock_context

        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(self.event, {}, self.mock_workspace)

        self.assertIn("Unable to correlate the datasets", str(context.exception))

    @patch("aws.osml.geoagents.spatial.correlation_tool.LocalAssets")
    @patch("aws.osml.geoagents.spatial.correlation_tool.read_geo_data_frame")
    def test_read_geo_data_frame_error(self, mock_read_gdf, mock_local_assets):
        """Test error handling when reading geodataframe fails."""
        # Setup LocalAssets mock
        mock_context = MagicMock()
        mock_context.__enter__.return_value = (self.sample_item1, {"data": Path("/tmp/test/data1.parquet")})
        mock_local_assets.return_value = mock_context

        # Make read_geo_data_frame fail
        mock_read_gdf.side_effect = Exception("Failed to read geodataframe")

        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(self.event, {}, self.mock_workspace)

        self.assertIn("Unable to correlate the datasets", str(context.exception))


if __name__ == "__main__":
    unittest.main()
