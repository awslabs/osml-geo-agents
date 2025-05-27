#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import geopandas as gpd
from shapely.geometry import Point, Polygon

from aws.osml.geoagents.common import ToolExecutionError, Workspace
from aws.osml.geoagents.spatial.summarize_tool import SummarizeTool


class TestSummarizeTool(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.tool = SummarizeTool()
        self.workspace = Mock(spec=Workspace)

    def create_point_gdf(self):
        """Helper to create a test GeoDataFrame with point geometries"""
        # Create sample data with different column types
        data = {
            "geometry": [Point(0, 0), Point(1, 1), Point(2, 2)],
            "name": ["Point A", "Point B", "Point C"],
            "value": [10, 20, 30],
            "score": [0.5, 1.5, 2.5],
            "active": [True, False, True],
            "timestamp": [datetime(2025, 1, 1), datetime(2025, 1, 2), datetime(2025, 1, 3)],
        }
        gdf = gpd.GeoDataFrame(data)
        return gdf

    def create_polygon_gdf(self):
        """Helper to create a test GeoDataFrame with polygon geometries"""
        # Create sample polygons
        polygons = [
            Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
            Polygon([(1, 1), (2, 1), (2, 2), (1, 2)]),
        ]
        data = {"geometry": polygons, "area_name": ["Zone A", "Zone B"], "area_size": [1.0, 1.0]}
        gdf = gpd.GeoDataFrame(data)
        return gdf

    def create_gdf_with_metadata(self):
        """Helper to create a GeoDataFrame with column metadata"""
        gdf = self.create_point_gdf()
        # Add metadata using attrs property
        gdf.attrs["column-descriptions"] = {
            "name": "Location name",
            "value": "Measured intensity value",
            "score": "Confidence score",
        }
        return gdf

    def test_init(self):
        """Test SummarizeTool initialization."""
        self.assertEqual(self.tool.action_group, "SpatialReasoning")
        self.assertEqual(self.tool.function_name, "SUMMARIZE")

    @patch("aws.osml.geoagents.spatial.summarize_tool.LocalAssets")
    @patch("aws.osml.geoagents.spatial.summarize_tool.read_geo_data_frame")
    def test_handler_with_points(self, mock_read_gdf, mock_context_manager):
        """Test handler with point geometry dataset."""
        # Setup mock context manager
        mock_context = Mock()
        mock_enter = Mock()
        mock_exit = Mock()
        mock_context.__enter__ = mock_enter
        mock_enter.return_value = (None, {0: Path("/tmp/test.geojson")})
        mock_context.__exit__ = mock_exit
        mock_exit.return_value = None
        mock_context_manager.return_value = mock_context
        gdf = self.create_point_gdf()
        mock_read_gdf.return_value = gdf

        # Create test event
        event = {
            "actionGroup": "SpatialReasoning",
            "function": "SUMMARIZE",
            "parameters": [{"name": "dataset", "value": "georef:test-dataset", "type": "string"}],
        }

        # Execute handler
        result = self.tool.handler(event, {}, self.workspace)

        # Verify response
        response_text = str(result["response"])

        # Check for expected content in response
        self.assertIn("Dataset georef:test-dataset contains 3 features.", response_text)
        self.assertIn("Dataset bounds (min_x, min_y, max_x, max_y): 0.000000, 0.000000, 2.000000, 2.000000", response_text)
        self.assertIn("geometry: Contains spatial features of type(s): Point", response_text)
        self.assertIn("name: General column", response_text)
        self.assertIn("value: Numeric column (int64) ranging from 10 to 30", response_text)
        self.assertIn("score: Numeric column (float64) ranging from 0.5 to 2.5", response_text)
        self.assertIn("active: Boolean column", response_text)
        self.assertIn("timestamp: Date/time column", response_text)

    @patch("aws.osml.geoagents.spatial.summarize_tool.LocalAssets")
    @patch("aws.osml.geoagents.spatial.summarize_tool.read_geo_data_frame")
    def test_handler_with_polygons(self, mock_read_gdf, mock_context_manager):
        """Test handler with polygon geometry dataset."""
        # Setup mock context manager
        mock_context = Mock()
        mock_enter = Mock()
        mock_exit = Mock()
        mock_context.__enter__ = mock_enter
        mock_enter.return_value = (None, {0: Path("/tmp/test.geojson")})
        mock_context.__exit__ = mock_exit
        mock_exit.return_value = None
        mock_context_manager.return_value = mock_context
        gdf = self.create_polygon_gdf()
        mock_read_gdf.return_value = gdf

        # Create test event
        event = {
            "actionGroup": "SpatialReasoning",
            "function": "SUMMARIZE",
            "parameters": [{"name": "dataset", "value": "georef:test-dataset", "type": "string"}],
        }

        # Execute handler
        result = self.tool.handler(event, {}, self.workspace)

        # Verify response
        response_text = str(result["response"])

        # Check for expected content in response
        self.assertIn("Dataset georef:test-dataset contains 2 features.", response_text)
        self.assertIn("Dataset bounds (min_x, min_y, max_x, max_y): 0.000000, 0.000000, 2.000000, 2.000000", response_text)
        self.assertIn("geometry: Contains spatial features of type(s): Polygon", response_text)
        self.assertIn("area_name: General column", response_text)
        self.assertIn("area_size: Numeric column (float64) ranging from 1.0 to 1.0", response_text)

    @patch("aws.osml.geoagents.spatial.summarize_tool.LocalAssets")
    @patch("aws.osml.geoagents.spatial.summarize_tool.read_geo_data_frame")
    def test_handler_with_metadata(self, mock_read_gdf, mock_context_manager):
        """Test handler processes column metadata correctly."""
        # Setup mock context manager
        mock_context = Mock()
        mock_enter = Mock()
        mock_exit = Mock()
        mock_context.__enter__ = mock_enter
        mock_enter.return_value = (None, {0: Path("/tmp/test.geojson")})
        mock_context.__exit__ = mock_exit
        mock_exit.return_value = None
        mock_context_manager.return_value = mock_context
        gdf = self.create_gdf_with_metadata()
        mock_read_gdf.return_value = gdf

        # Create test event
        event = {
            "actionGroup": "SpatialReasoning",
            "function": "SUMMARIZE",
            "parameters": [{"name": "dataset", "value": "georef:test-dataset", "type": "string"}],
        }

        # Execute handler
        result = self.tool.handler(event, {}, self.workspace)

        # Verify response
        response_text = str(result["response"])

        # Check for bounding box and metadata in response
        self.assertIn("Dataset bounds (min_x, min_y, max_x, max_y): 0.000000, 0.000000, 2.000000, 2.000000", response_text)
        self.assertIn("name: General column (Location name)", response_text)
        self.assertIn("value: Numeric column (int64) ranging from 10 to 30 (Measured intensity value)", response_text)
        self.assertIn("score: Numeric column (float64) ranging from 0.5 to 2.5 (Confidence score)", response_text)

    @patch("aws.osml.geoagents.spatial.summarize_tool.LocalAssets")
    def test_handler_error_handling(self, mock_context_manager):
        """Test various error conditions in handler."""
        # Test context manager error
        mock_context = Mock()
        mock_enter = Mock()
        mock_exit = Mock()
        mock_context.__enter__ = mock_enter
        mock_enter.side_effect = Exception("Failed to load assets")
        mock_context.__exit__ = mock_exit
        mock_exit.return_value = None
        mock_context_manager.return_value = mock_context

        event = {
            "actionGroup": "SpatialReasoning",
            "function": "SUMMARIZE",
            "parameters": [{"name": "dataset", "value": "georef:test-dataset", "type": "string"}],
        }

        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(event, {}, self.workspace)

        self.assertIn("Unable to summarize the dataset", str(context.exception))


if __name__ == "__main__":
    unittest.main()
