#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import geopandas as gpd
from shapely.geometry import Point, Polygon

from aws.osml.geoagents.common import Georeference, Workspace
from aws.osml.geoagents.spatial.summarize_operation import summarize_operation


class TestSummarizeOperation(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a mock workspace
        self.mock_workspace = Mock(spec=Workspace)
        self.mock_workspace.session_local_path = "/tmp"

        # Create a mock georeference
        self.dataset_georef = Mock(spec=Georeference)
        self.dataset_georef.__str__ = Mock(return_value="georef:test-dataset")

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

    @patch("aws.osml.geoagents.spatial.summarize_operation.LocalAssets")
    @patch("aws.osml.geoagents.spatial.summarize_operation.read_geo_data_frame")
    def test_operation_with_points(self, mock_read_gdf, mock_context_manager):
        """Test operation with point geometry dataset."""
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

        # Execute operation
        result = summarize_operation(dataset_georef=self.dataset_georef, workspace=self.mock_workspace)

        # Verify response
        # Check for expected content in response
        self.assertIn("Dataset georef:test-dataset contains 3 features.", result)
        self.assertIn("Dataset bounds (min_x, min_y, max_x, max_y): 0.000000, 0.000000, 2.000000, 2.000000", result)
        self.assertIn("geometry: Contains spatial features of type(s): Point", result)
        self.assertIn("name: General column", result)
        self.assertIn("value: Numeric column (int64) ranging from 10 to 30", result)
        self.assertIn("score: Numeric column (float64) ranging from 0.5 to 2.5", result)
        self.assertIn("active: Boolean column", result)
        self.assertIn("timestamp: Date/time column", result)

    @patch("aws.osml.geoagents.spatial.summarize_operation.LocalAssets")
    @patch("aws.osml.geoagents.spatial.summarize_operation.read_geo_data_frame")
    def test_operation_with_polygons(self, mock_read_gdf, mock_context_manager):
        """Test operation with polygon geometry dataset."""
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

        # Execute operation
        result = summarize_operation(dataset_georef=self.dataset_georef, workspace=self.mock_workspace)

        # Verify response
        # Check for expected content in response
        self.assertIn("Dataset georef:test-dataset contains 2 features.", result)
        self.assertIn("Dataset bounds (min_x, min_y, max_x, max_y): 0.000000, 0.000000, 2.000000, 2.000000", result)
        self.assertIn("geometry: Contains spatial features of type(s): Polygon", result)
        self.assertIn("area_name: General column", result)
        self.assertIn("area_size: Numeric column (float64) ranging from 1.0 to 1.0", result)

    @patch("aws.osml.geoagents.spatial.summarize_operation.LocalAssets")
    @patch("aws.osml.geoagents.spatial.summarize_operation.read_geo_data_frame")
    def test_operation_with_metadata(self, mock_read_gdf, mock_context_manager):
        """Test operation processes column metadata correctly."""
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

        # Execute operation
        result = summarize_operation(dataset_georef=self.dataset_georef, workspace=self.mock_workspace)

        # Verify response
        # Check for bounding box and metadata in response
        self.assertIn("Dataset bounds (min_x, min_y, max_x, max_y): 0.000000, 0.000000, 2.000000, 2.000000", result)
        self.assertIn("name: General column (Location name)", result)
        self.assertIn("value: Numeric column (int64) ranging from 10 to 30 (Measured intensity value)", result)
        self.assertIn("score: Numeric column (float64) ranging from 0.5 to 2.5 (Confidence score)", result)


if __name__ == "__main__":
    unittest.main()
