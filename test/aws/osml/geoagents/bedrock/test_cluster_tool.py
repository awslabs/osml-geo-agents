#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from aws.osml.geoagents.bedrock import ClusterTool, ToolExecutionError
from aws.osml.geoagents.common import GeoDataReference, Workspace


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
        self.context = {}

        # Create a sample event with required parameters
        self.event = {
            "agent": "test_agent",
            "actionGroup": "SpatialReasoning",
            "function": "CLUSTER",
            "parameters": [
                {"name": "dataset", "value": "stac:1234", "type": "string"},
                {"name": "distance", "value": "100", "type": "string"},
            ],
            "messageVersion": "1.0",
        }

    def test_constructor(self):
        """Test that the constructor properly initializes the action group and function name."""
        self.assertEqual(self.tool.action_group, "SpatialReasoning")
        self.assertEqual(self.tool.function_name, "CLUSTER")

    @patch("aws.osml.geoagents.bedrock.cluster_tool.cluster_operation")
    def test_handler_successful_clustering(self, mock_cluster_operation):
        """Test successful clustering with valid parameters."""
        # Mock the cluster_operation function to return a predefined result
        mock_cluster_operation.return_value = (
            "Found 3 clusters in dataset stac:1234 using a distance threshold of 100.0 meters. "
            "\nAll clusters are available in stac:CLUSTER-20250612 with the following assets:\n"
            "- cluster-0: 4 features\n"
            "- cluster-1: 5 features\n"
            "- cluster-2: 3 features\n"
        )

        # Call the handler
        result = self.tool.handler(self.event, self.context, self.mock_workspace)

        # Verify cluster_operation was called with the correct parameters
        mock_cluster_operation.assert_called_once_with(
            dataset_georef=GeoDataReference("stac:1234"),
            distance_meters=100.0,
            max_clusters=None,
            workspace=self.mock_workspace,
            function_name=self.tool.function_name,
        )

        # Parse the result
        result_body = json.loads(result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"])
        result_text = result_body.get("result", "")

        # Verify the result contains information about clusters
        self.assertIn("Found 3 clusters", result_text)
        self.assertIn("stac:1234", result_text)
        self.assertIn("stac:CLUSTER-20250612", result_text)
        self.assertIn("cluster-0: 4 features", result_text)
        self.assertIn("cluster-1: 5 features", result_text)
        self.assertIn("cluster-2: 3 features", result_text)

    @patch("aws.osml.geoagents.bedrock.cluster_tool.cluster_operation")
    def test_handler_with_max_clusters(self, mock_cluster_operation):
        """Test clustering with max_clusters parameter."""
        # Add max_clusters parameter to the event
        event_with_max = self.event.copy()
        event_with_max["parameters"] = self.event["parameters"].copy()
        event_with_max["parameters"].append({"name": "max_clusters", "value": 2, "type": "number"})

        # Mock the cluster_operation function to return a predefined result
        mock_cluster_operation.return_value = (
            "Found 3 clusters in dataset stac:1234 using a distance threshold of 100.0 meters. "
            "Saved the 2 largest clusters as requested. "
            "\nAll clusters are available in stac:CLUSTER-20250612 with the following assets:\n"
            "- cluster-1: 5 features\n"
            "- cluster-0: 4 features\n"
        )

        # Call the handler
        result = self.tool.handler(event_with_max, self.context, self.mock_workspace)

        # Verify cluster_operation was called with the correct parameters
        mock_cluster_operation.assert_called_once_with(
            dataset_georef=GeoDataReference("stac:1234"),
            distance_meters=100.0,
            max_clusters=2,
            workspace=self.mock_workspace,
            function_name=self.tool.function_name,
        )

        # Parse the result
        result_body = json.loads(result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"])
        result_text = result_body.get("result", "")

        # Verify the result mentions limiting to max clusters
        self.assertIn("Found 3 clusters", result_text)
        self.assertIn("Saved the 2 largest clusters", result_text)
        self.assertIn("cluster-1: 5 features", result_text)
        self.assertIn("cluster-0: 4 features", result_text)
        self.assertNotIn("cluster-2", result_text)

    @patch("aws.osml.geoagents.bedrock.cluster_tool.cluster_operation")
    def test_handler_no_clusters_found(self, mock_cluster_operation):
        """Test handling of datasets where no clusters are found."""
        # Mock the cluster_operation function to return a predefined result with no clusters
        mock_cluster_operation.return_value = (
            "Found 0 clusters in dataset stac:1234 using a distance threshold of 100.0 meters. "
            "\nAll clusters are available in stac:CLUSTER-20250612 with the following assets:\n"
        )

        # Call the handler
        result = self.tool.handler(self.event, self.context, self.mock_workspace)

        # Verify cluster_operation was called with the correct parameters
        mock_cluster_operation.assert_called_once_with(
            dataset_georef=GeoDataReference("stac:1234"),
            distance_meters=100.0,
            max_clusters=None,
            workspace=self.mock_workspace,
            function_name=self.tool.function_name,
        )

        # Parse the result
        result_body = json.loads(result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"])
        result_text = result_body.get("result", "")

        # Verify the result indicates no clusters found
        self.assertIn("Found 0 clusters", result_text)

    def test_handler_missing_required_parameter(self):
        """Test handling of missing required parameters."""
        # Create event with missing distance parameter
        event_missing_param = {
            "agent": "test_agent",
            "actionGroup": "SpatialReasoning",
            "function": "CLUSTER",
            "parameters": [
                {"name": "dataset", "value": "stac:1234", "type": "string"},
                # distance parameter is missing
            ],
        }

        # Call the handler and expect an exception
        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(event_missing_param, self.context, self.mock_workspace)

        # Verify the error message
        self.assertIn("Missing required parameter", str(context.exception))
        self.assertIn("distance", str(context.exception))

    def test_handler_invalid_distance_parameter(self):
        """Test handling of invalid distance parameter."""
        # Create event with invalid distance parameter
        event_invalid_param = {
            "agent": "test_agent",
            "actionGroup": "SpatialReasoning",
            "function": "CLUSTER",
            "parameters": [
                {"name": "dataset", "value": "stac:1234", "type": "string"},
                {"name": "distance", "value": "not_a_number", "type": "string"},
            ],
        }

        # Call the handler and expect an exception
        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(event_invalid_param, self.context, self.mock_workspace)

        # Verify the error message
        self.assertIn("Unable to parse", str(context.exception))
        self.assertIn("distance", str(context.exception))

    @patch("aws.osml.geoagents.bedrock.cluster_tool.cluster_operation")
    def test_handler_error_handling(self, mock_cluster_operation):
        """Test error handling when cluster_operation raises an exception."""
        # Mock the cluster_operation function to raise an exception
        mock_cluster_operation.side_effect = ValueError("Test error message")

        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(self.event, self.context, self.mock_workspace)

        self.assertIn("Unable to cluster the dataset", str(context.exception))
        self.assertIn("Test error message", str(context.exception))


if __name__ == "__main__":
    unittest.main()
