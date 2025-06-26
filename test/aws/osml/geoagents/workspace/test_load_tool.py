#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from aws.osml.geoagents.bedrock import ToolExecutionError
from aws.osml.geoagents.common import Georeference, Workspace
from aws.osml.geoagents.workspace import LoadTool


class TestLoadTool(unittest.TestCase):
    """Unit tests for the LoadTool class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.tool = LoadTool()
        self.mock_workspace = Mock(spec=Workspace)
        self.mock_workspace.session_local_path = Path("/tmp/osml-geo-agents/test")

        # Create a sample event
        self.event = {
            "agent": "test_agent",
            "actionGroup": "WorkspaceActions",
            "function": "LOAD",
            "parameters": [
                {"name": "s3_url", "value": "s3://test-bucket/test-key.tif", "type": "string"},
                {"name": "dataset_name", "value": "Test Dataset", "type": "string"},
            ],
        }

    @patch("aws.osml.geoagents.workspace.load_tool.secrets")
    def test_handler_successful_load(self, mock_secrets):
        """Test successful loading of a dataset from S3."""
        # Mock the secrets.token_hex to return a predictable value
        mock_secrets.token_hex.return_value = "abcd1234"

        # Mock the S3 client and download_file method
        self.mock_workspace.s3_client = Mock()
        self.mock_workspace.s3_transfer_config = {}
        self.mock_workspace.create_item = Mock()

        # Mock the create_item to return a georeference
        mock_georef = Georeference.from_parts(item_id="abcd1234")
        self.mock_workspace.create_item.return_value = mock_georef

        # Call the handler
        result = self.tool.handler(self.event, {}, self.mock_workspace)

        # Verify the result
        self.assertIn("Successfully loaded dataset", str(result))
        self.assertIn(str(mock_georef), str(result))

        # Verify S3 client was called correctly
        self.mock_workspace.s3_client.download_file.assert_called_once()
        self.assertEqual(self.mock_workspace.s3_client.download_file.call_args[1]["Bucket"], "test-bucket")
        self.assertEqual(self.mock_workspace.s3_client.download_file.call_args[1]["Key"], "test-key.tif")

        # Verify create_item was called
        self.mock_workspace.create_item.assert_called_once()

    def test_handler_missing_s3_url(self):
        """Test handling of missing s3_url parameter."""
        # Create an event with missing s3_url
        event_missing_url = {
            "agent": "test_agent",
            "actionGroup": "WorkspaceActions",
            "function": "LOAD",
            "parameters": [
                {"name": "dataset_name", "value": "Test Dataset", "type": "string"},
            ],
        }

        # Call the handler and expect an exception
        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(event_missing_url, {}, self.mock_workspace)

        # Verify the error message
        self.assertIn("Missing required parameter", str(context.exception))
        self.assertIn("s3_url", str(context.exception))

    def test_handler_invalid_s3_url(self):
        """Test handling of invalid s3_url parameter."""
        # Create an event with invalid s3_url
        event_invalid_url = {
            "agent": "test_agent",
            "actionGroup": "WorkspaceActions",
            "function": "LOAD",
            "parameters": [
                {"name": "s3_url", "value": "http://test-bucket/test-key.tif", "type": "string"},
                {"name": "dataset_name", "value": "Test Dataset", "type": "string"},
            ],
        }

        # Call the handler and expect an exception
        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(event_invalid_url, {}, self.mock_workspace)

        # Verify the error message
        self.assertIn("Invalid S3 URL", str(context.exception))
        self.assertIn("must start with 's3://'", str(context.exception))

    @patch("aws.osml.geoagents.workspace.load_tool.secrets")
    def test_handler_s3_download_error(self, mock_secrets):
        """Test handling of S3 download error."""
        # Mock the secrets.token_hex to return a predictable value
        mock_secrets.token_hex.return_value = "abcd1234"

        # Mock the S3 client to raise an exception
        self.mock_workspace.s3_client = Mock()
        self.mock_workspace.s3_transfer_config = {}
        self.mock_workspace.s3_client.download_file.side_effect = Exception("S3 download failed")

        # Call the handler and expect an exception
        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(self.event, {}, self.mock_workspace)

        # Verify the error message
        self.assertIn("Failed to download asset from S3", str(context.exception))

    @patch("aws.osml.geoagents.workspace.load_tool.secrets")
    def test_handler_create_error(self, mock_secrets):
        """Test handling of create error."""
        # Mock the secrets.token_hex to return a predictable value
        mock_secrets.token_hex.return_value = "abcd1234"

        # Mock the S3 client
        self.mock_workspace.s3_client = Mock()
        self.mock_workspace.s3_transfer_config = {}

        # Mock the create_item to raise an exception
        self.mock_workspace.create_item = Mock(side_effect=Exception("Create failed"))

        # Call the handler and expect an exception
        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(self.event, {}, self.mock_workspace)

        # Verify the error message
        self.assertIn("Failed to create item in workspace", str(context.exception))

    @patch("aws.osml.geoagents.workspace.load_tool.secrets")
    def test_handler_without_dataset_name(self, mock_secrets):
        """Test loading without a dataset name."""
        # Mock the secrets.token_hex to return a predictable value
        mock_secrets.token_hex.return_value = "abcd1234"

        # Create an event without dataset_name
        event_no_name = {
            "agent": "test_agent",
            "actionGroup": "WorkspaceActions",
            "function": "LOAD",
            "parameters": [
                {"name": "s3_url", "value": "s3://test-bucket/test-key.tif", "type": "string"},
            ],
        }

        # Mock the S3 client
        self.mock_workspace.s3_client = Mock()
        self.mock_workspace.s3_transfer_config = {}

        # Mock the create_item to return a georeference
        mock_georef = Georeference.from_parts(item_id="abcd1234")
        self.mock_workspace.create_item = Mock(return_value=mock_georef)

        # Call the handler
        result = self.tool.handler(event_no_name, {}, self.mock_workspace)

        # Verify the result
        self.assertIn("Successfully loaded dataset", str(result))

        # Verify create_item was called with the basename as the title
        call_args = self.mock_workspace.create_item.call_args
        item = call_args[1]["item"]
        self.assertEqual(item.properties.get("title"), "test-key.tif")

    @patch("aws.osml.geoagents.workspace.load_tool.Path")
    @patch("aws.osml.geoagents.workspace.load_tool.secrets")
    def test_handler_cleanup_on_success(self, mock_secrets, mock_path):
        """Test that temporary files are cleaned up on success."""
        # Mock the secrets.token_hex to return a predictable value
        mock_secrets.token_hex.return_value = "abcd1234"

        # Mock the Path and its methods
        mock_file_path = Mock()
        mock_file_path.parent.mkdir = Mock()
        mock_file_path.exists.return_value = True
        mock_file_path.unlink = Mock()
        mock_file_path.absolute.return_value = "/tmp/osml-geo-agents/test/temp/test-key.tif"
        mock_path.return_value = mock_file_path

        # Mock the S3 client
        self.mock_workspace.s3_client = Mock()
        self.mock_workspace.s3_transfer_config = {}

        # Mock the create_item to return a georeference
        mock_georef = Georeference.from_parts(item_id="abcd1234")
        self.mock_workspace.create_item = Mock(return_value=mock_georef)

        # Call the handler
        self.tool.handler(self.event, {}, self.mock_workspace)

        # Verify the file was cleaned up
        mock_file_path.exists.assert_called_once()
        mock_file_path.unlink.assert_called_once()

    @patch("aws.osml.geoagents.workspace.load_tool.Path")
    @patch("aws.osml.geoagents.workspace.load_tool.secrets")
    def test_handler_cleanup_on_error(self, mock_secrets, mock_path):
        """Test that temporary files are cleaned up on error."""
        # Mock the secrets.token_hex to return a predictable value
        mock_secrets.token_hex.return_value = "abcd1234"

        # Mock the Path and its methods
        mock_file_path = Mock()
        mock_file_path.parent.mkdir = Mock()
        mock_file_path.exists.return_value = True
        mock_file_path.unlink = Mock()
        mock_file_path.absolute.return_value = "/tmp/osml-geo-agents/test/temp/test-key.tif"
        mock_path.return_value = mock_file_path

        # Mock the S3 client
        self.mock_workspace.s3_client = Mock()
        self.mock_workspace.s3_transfer_config = {}

        # Mock the create_item to raise an exception
        self.mock_workspace.create_item = Mock(side_effect=Exception("Create failed"))

        # Call the handler and expect an exception
        with self.assertRaises(ToolExecutionError):
            self.tool.handler(self.event, {}, self.mock_workspace)

        # Verify the file was cleaned up
        mock_file_path.exists.assert_called_once()
        mock_file_path.unlink.assert_called_once()


if __name__ == "__main__":
    unittest.main()
