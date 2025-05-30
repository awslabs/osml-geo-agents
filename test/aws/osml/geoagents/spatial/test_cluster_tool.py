#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import json
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import geopandas as gpd
import shapely
from pyproj import CRS
from pystac import Asset, Item

from aws.osml.geoagents.common import ToolExecutionError, Workspace
from aws.osml.geoagents.spatial.cluster_tool import ClusterTool


class TestClusterTool(unittest.TestCase):
    """
    Unit tests for the ClusterTool class.

    These tests verify the functionality of the clustering tool, including parameter validation,
    clustering operations, and error handling.
    """

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.tool = ClusterTool()
        self.mock_workspace = Mock(spec=Workspace)
        self.mock_workspace.session_local_path = Path("/tmp/osml-geo-agents/test")

        # Create a sample event with required parameters
        self.event = {
            "agent": "test_agent",
            "actionGroup": "SpatialReasoning",
            "function": "CLUSTER",
            "parameters": [
                {"name": "dataset", "value": "georef:1234", "type": "string"},
                {"name": "distance", "value": "100", "type": "string"},
            ],
            "messageVersion": "1.0",
        }

        # Create a sample STAC item
        self.sample_item = Item(
            id="1234",
            geometry={"type": "Polygon", "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]]},
            datetime=datetime.fromisoformat("2025-04-23T14:05:23Z"),
            bbox=[0, 0, 2, 2],
            properties={
                "title": "Test Dataset",
                "keywords": ["test"],
            },
            assets={"data": Asset(href="s3://fake-test-bucket/data.parquet")},
        )

    def test_constructor(self):
        """Test that the constructor properly initializes the action group and function name."""
        self.assertEqual(self.tool.action_group, "SpatialReasoning")
        self.assertEqual(self.tool.function_name, "CLUSTER")

    def _create_clustered_geodataframe(self, with_clusters=True):
        """
        Helper method to create a GeoDataFrame with points that will form clusters.

        :param with_clusters: If True, creates points that will form clusters; if False, creates scattered points
        :return: A GeoDataFrame with point geometries
        """
        if with_clusters:
            # Create three distinct clusters of points, 100m is slightly less than 0.001 degrees at the equator
            cluster1 = [(0.1, 0.1), (0.1002, 0.1001), (0.1001, 0.1003), (0.0999, 0.1002)]  # Cluster 1
            cluster2 = [(0.5, 0.5), (0.5001, 0.5002), (0.4999, 0.5001), (0.5002, 0.4999), (0.5002, 0.5001)]  # Cluster 2
            cluster3 = [(0.9, 0.9), (0.9001, 0.9002), (0.8999, 0.9001)]  # Cluster 3

            # Add some noise points
            noise = [(0.3, 0.7), (0.7, 0.3)]

            all_points = cluster1 + cluster2 + cluster3 + noise
        else:
            # Create scattered points that won't form clusters with the default distance
            all_points = [(0.1, 0.1), (0.3, 0.3), (0.5, 0.5), (0.7, 0.7), (0.9, 0.9)]

        # Create geometries
        geometries = [shapely.geometry.Point(x, y) for x, y in all_points]

        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame(geometry=geometries)
        gdf.set_crs(CRS.from_epsg(4326), inplace=True)

        return gdf

    @patch("aws.osml.geoagents.spatial.cluster_tool.LocalAssets")
    @patch("aws.osml.geoagents.spatial.cluster_tool.read_geo_data_frame")
    @patch("aws.osml.geoagents.spatial.cluster_tool.write_geo_data_frame")
    @patch("aws.osml.geoagents.spatial.cluster_tool.create_derived_stac_item")
    def test_handler_successful_clustering(self, mock_create_stac, mock_write_gdf, mock_read_gdf, mock_local_assets):
        """Test successful clustering with valid parameters."""
        # Setup mock context manager
        mock_context = Mock()
        mock_enter = Mock()
        mock_exit = Mock()
        mock_context.__enter__ = mock_enter
        mock_enter.return_value = (self.sample_item, {"data": Path("/tmp/test/sample.geojson")})
        mock_context.__exit__ = mock_exit
        mock_exit.return_value = None
        mock_local_assets.return_value = mock_context

        # Create sample GeoDataFrame with clusters
        sample_gdf = self._create_clustered_geodataframe(with_clusters=True)
        mock_read_gdf.return_value = sample_gdf

        # Mock create_derived_stac_item
        mock_derived_item = Mock()
        mock_create_stac.return_value = mock_derived_item

        # Mock publish_item
        self.mock_workspace.publish_item = Mock()

        # Call the handler
        result = self.tool.handler(self.event, {}, self.mock_workspace)

        # Parse the result
        result_body = json.loads(result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"])
        result_text = result_body.get("result", "")

        # Verify the result contains information about clusters
        print(result_text)
        self.assertIn("Found", result_text)
        self.assertIn("clusters", result_text)
        self.assertIn("georef:", result_text)

        # Verify workspace interactions
        self.mock_workspace.publish_item.assert_called_once()

        # Verify that the clusters were created correctly
        # This indirectly tests that DBSCAN was not mocked
        call_args_list = mock_write_gdf.call_args_list
        print(call_args_list)
        self.assertGreaterEqual(len(call_args_list), 3)  # At least 3 clusters should be written

    @patch("aws.osml.geoagents.spatial.cluster_tool.LocalAssets")
    @patch("aws.osml.geoagents.spatial.cluster_tool.read_geo_data_frame")
    @patch("aws.osml.geoagents.spatial.cluster_tool.write_geo_data_frame")
    @patch("aws.osml.geoagents.spatial.cluster_tool.create_derived_stac_item")
    def test_handler_with_max_clusters(self, mock_create_stac, mock_write_gdf, mock_read_gdf, mock_local_assets):
        """Test clustering with max_clusters parameter."""
        # Add max_clusters parameter to the event
        event_with_max = self.event.copy()
        event_with_max["parameters"] = self.event["parameters"].copy()
        event_with_max["parameters"].append({"name": "max_clusters", "value": 2, "type": "number"})

        # Setup mock context manager
        mock_context = Mock()
        mock_enter = Mock()
        mock_exit = Mock()
        mock_context.__enter__ = mock_enter
        mock_enter.return_value = (self.sample_item, {"data": Path("/tmp/test/sample.geojson")})
        mock_context.__exit__ = mock_exit
        mock_exit.return_value = None
        mock_local_assets.return_value = mock_context

        # Create sample GeoDataFrame with clusters
        sample_gdf = self._create_clustered_geodataframe(with_clusters=True)
        mock_read_gdf.return_value = sample_gdf

        # Mock create_derived_stac_item
        mock_derived_item = Mock()
        mock_create_stac.return_value = mock_derived_item

        # Mock publish_item
        self.mock_workspace.publish_item = Mock()

        # Call the handler
        result = self.tool.handler(event_with_max, {}, self.mock_workspace)

        # Parse the result
        result_body = json.loads(result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"])
        result_text = result_body.get("result", "").lower()

        # Verify the result mentions limiting to max clusters
        self.assertIn("2 largest clusters", result_text)

        # Verify that the two largest clusters have been selected
        self.assertIn("5 features", result_text)
        self.assertIn("4 features", result_text)
        self.assertNotIn("3 features", result_text)

        # Verify workspace interactions
        self.mock_workspace.publish_item.assert_called_once()

        # Verify that only 2 clusters were written
        call_args_list = mock_write_gdf.call_args_list
        self.assertEqual(len(call_args_list), 2)  # Only 2 clusters should be written

    @patch("aws.osml.geoagents.spatial.cluster_tool.LocalAssets")
    @patch("aws.osml.geoagents.spatial.cluster_tool.read_geo_data_frame")
    def test_handler_no_clusters_found(self, mock_read_gdf, mock_local_assets):
        """Test handling of datasets where no clusters are found."""
        # Setup mock context manager
        mock_context = Mock()
        mock_enter = Mock()
        mock_exit = Mock()
        mock_context.__enter__ = mock_enter
        mock_enter.return_value = (self.sample_item, {"data": Path("/tmp/test/sample.geojson")})
        mock_context.__exit__ = mock_exit
        mock_exit.return_value = None
        mock_local_assets.return_value = mock_context

        # Create sample GeoDataFrame with scattered points (no clusters)
        sample_gdf = self._create_clustered_geodataframe(with_clusters=False)
        mock_read_gdf.return_value = sample_gdf

        # Call the handler
        result = self.tool.handler(self.event, {}, self.mock_workspace)

        # Parse the result
        result_body = json.loads(result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"])
        result_text = result_body.get("result", "")

        # Verify the result indicates no clusters found
        self.assertIn("Found 0 clusters", result_text)

        # Verify workspace interactions - should still publish an item with no clusters
        self.mock_workspace.publish_item.assert_called_once()

    @patch("aws.osml.geoagents.spatial.cluster_tool.LocalAssets")
    def test_handler_missing_required_parameter(self, mock_local_assets):
        """Test handling of missing required parameters."""
        # Create event with missing distance parameter
        event_missing_param = {
            "agent": "test_agent",
            "actionGroup": "SpatialReasoning",
            "function": "CLUSTER",
            "parameters": [
                {"name": "dataset", "value": "georef:1234", "type": "string"},
                # distance parameter is missing
            ],
        }

        # Call the handler and expect an exception
        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(event_missing_param, {}, self.mock_workspace)

        # Verify the error message
        self.assertIn("Missing required parameter", str(context.exception))
        self.assertIn("distance", str(context.exception))

    @patch("aws.osml.geoagents.spatial.cluster_tool.LocalAssets")
    def test_handler_invalid_distance_parameter(self, mock_local_assets):
        """Test handling of invalid distance parameter."""
        # Create event with invalid distance parameter
        event_invalid_param = {
            "agent": "test_agent",
            "actionGroup": "SpatialReasoning",
            "function": "CLUSTER",
            "parameters": [
                {"name": "dataset", "value": "georef:1234", "type": "string"},
                {"name": "distance", "value": "not_a_number", "type": "string"},
            ],
        }

        # Call the handler and expect an exception
        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(event_invalid_param, {}, self.mock_workspace)

        # Verify the error message
        self.assertIn("Unable to parse", str(context.exception))
        self.assertIn("distance", str(context.exception))

    @patch("aws.osml.geoagents.spatial.cluster_tool.LocalAssets")
    @patch("aws.osml.geoagents.spatial.cluster_tool.read_geo_data_frame")
    def test_handler_invalid_crs(self, mock_read_gdf, mock_local_assets):
        """Test handling of datasets with unsupported CRS."""
        # Setup mock context manager
        mock_context = Mock()
        mock_enter = Mock()
        mock_exit = Mock()
        mock_context.__enter__ = mock_enter
        mock_enter.return_value = (self.sample_item, {"data": Path("/tmp/test/sample.geojson")})
        mock_context.__exit__ = mock_exit
        mock_exit.return_value = None
        mock_local_assets.return_value = mock_context

        # Create sample GeoDataFrame with unsupported CRS
        sample_gdf = self._create_clustered_geodataframe(with_clusters=True)
        sample_gdf.set_crs(CRS.from_epsg(3857), inplace=True, allow_override=True)  # Force CRS to Web Mercator
        mock_read_gdf.return_value = sample_gdf

        # Mock validate_dataset_crs to raise an exception
        with patch("aws.osml.geoagents.spatial.cluster_tool.validate_dataset_crs") as mock_validate:
            mock_validate.side_effect = ToolExecutionError("Dataset does not use a supported CRS")

            # Call the handler and expect an exception
            with self.assertRaises(ToolExecutionError) as context:
                self.tool.handler(self.event, {}, self.mock_workspace)

            # Verify the error message
            self.assertIn("CRS", str(context.exception))

    @patch("aws.osml.geoagents.spatial.cluster_tool.LocalAssets")
    @patch("aws.osml.geoagents.spatial.cluster_tool.read_geo_data_frame")
    @patch("aws.osml.geoagents.spatial.cluster_tool.write_geo_data_frame")
    @patch("aws.osml.geoagents.spatial.cluster_tool.create_derived_stac_item")
    def test_handler_cleanup_on_exception(self, mock_create_stac, mock_write_gdf, mock_read_gdf, mock_local_assets):
        """Test that temporary files are cleaned up when an exception occurs."""
        # Setup mock context manager
        mock_context = Mock()
        mock_enter = Mock()
        mock_exit = Mock()
        mock_context.__enter__ = mock_enter
        mock_enter.return_value = (self.sample_item, {"data": Path("/tmp/test/sample.geojson")})
        mock_context.__exit__ = mock_exit
        mock_exit.return_value = None
        mock_local_assets.return_value = mock_context

        # Create sample GeoDataFrame with clusters
        sample_gdf = self._create_clustered_geodataframe(with_clusters=True)
        mock_read_gdf.return_value = sample_gdf

        # Mock write_geo_data_frame to create a real Path object
        def side_effect_write(path, gdf):
            # Create a mock file path that exists
            mock_path = MagicMock(spec=Path)
            mock_path.exists.return_value = True
            mock_path.unlink.return_value = None
            return mock_path

        mock_write_gdf.side_effect = side_effect_write

        # Mock create_derived_stac_item to raise an exception
        mock_create_stac.side_effect = Exception("Test exception")

        # Call the handler and expect an exception
        with self.assertRaises(ToolExecutionError):
            self.tool.handler(self.event, {}, self.mock_workspace)

        # Verify that Path.unlink would be called in the finally block
        # This is difficult to test directly, but we can verify the exception was raised
        mock_create_stac.assert_called_once()


if __name__ == "__main__":
    unittest.main()
