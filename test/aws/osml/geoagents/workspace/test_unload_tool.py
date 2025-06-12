#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

from pystac import Item

from aws.osml.geoagents.bedrock import ToolExecutionError
from aws.osml.geoagents.common import Georeference, Workspace
from aws.osml.geoagents.workspace import UnloadTool


class TestUnloadTool(unittest.TestCase):
    """Unit tests for the UnloadTool class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.tool = UnloadTool()
        self.mock_workspace = Mock(spec=Workspace)
        self.mock_workspace.session_local_path = Path("/tmp/osml-geo-agents/test")

        # Create a sample georef
        self.georef = Georeference.from_parts(item_id="test-item")

        # Create a sample event
        self.event = {
            "agent": "test_agent",
            "actionGroup": "WorkspaceActions",
            "function": "UNLOAD",
            "parameters": [
                {"name": "dataset", "value": str(self.georef), "type": "string"},
            ],
        }

    def test_handler_successful_unload(self):
        """Test successful unloading of a dataset."""
        # Create a sample item to be returned by get_item
        sample_item = Item(
            id="test-item", geometry=None, bbox=None, datetime=datetime.now(), properties={"title": "Test Dataset"}
        )

        # Mock the get_item method to return the sample item
        self.mock_workspace.get_item = Mock(return_value=sample_item)

        # Mock the delete_item method
        self.mock_workspace.delete_item = Mock()

        # Call the handler
        result = self.tool.handler(self.event, {}, self.mock_workspace)

        # Verify the result
        self.assertIn("Successfully removed dataset", str(result))
        self.assertIn(str(self.georef), str(result))
        self.assertIn("Test Dataset", str(result))

        # Verify get_item was called with the correct georef
        self.mock_workspace.get_item.assert_called_once_with(self.georef)

        # Verify delete_item was called with the correct georef
        self.mock_workspace.delete_item.assert_called_once_with(self.georef)

    def test_handler_missing_dataset_parameter(self):
        """Test handling of missing dataset parameter."""
        # Create an event with missing dataset parameter
        event_missing_dataset = {
            "agent": "test_agent",
            "actionGroup": "WorkspaceActions",
            "function": "UNLOAD",
            "parameters": [],
        }

        # Call the handler and expect an exception
        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(event_missing_dataset, {}, self.mock_workspace)

        # Verify the error message
        self.assertIn("Missing required parameter", str(context.exception))
        self.assertIn("dataset", str(context.exception))

    def test_handler_invalid_dataset_parameter(self):
        """Test handling of invalid dataset parameter."""
        # Create an event with invalid dataset parameter
        event_invalid_dataset = {
            "agent": "test_agent",
            "actionGroup": "WorkspaceActions",
            "function": "UNLOAD",
            "parameters": [
                {"name": "dataset", "value": "invalid-georef", "type": "string"},
            ],
        }

        # Call the handler and expect an exception
        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(event_invalid_dataset, {}, self.mock_workspace)

        # Verify the error message
        self.assertIn("Unable to construct a valid georeference", str(context.exception))

    def test_handler_get_item_error(self):
        """Test handling of errors when getting item details."""
        # Mock the get_item method to raise an exception
        self.mock_workspace.get_item = Mock(side_effect=Exception("Failed to get item"))

        # Call the handler and expect an exception
        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(self.event, {}, self.mock_workspace)

        # Verify the error message
        self.assertIn("Failed to remove dataset", str(context.exception))
        self.assertIn(str(self.georef), str(context.exception))

        # Verify get_item was called
        self.mock_workspace.get_item.assert_called_once()

        # Verify delete_item was not called
        self.mock_workspace.delete_item.assert_not_called()

    def test_handler_delete_item_error(self):
        """Test handling of errors when deleting an item."""
        # Create a sample item to be returned by get_item
        sample_item = Item(
            id="test-item", geometry=None, bbox=None, datetime=datetime.now(), properties={"title": "Test Dataset"}
        )

        # Mock the get_item method to return the sample item
        self.mock_workspace.get_item = Mock(return_value=sample_item)

        # Mock the delete_item method to raise an exception
        self.mock_workspace.delete_item = Mock(side_effect=Exception("Failed to delete item"))

        # Call the handler and expect an exception
        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(self.event, {}, self.mock_workspace)

        # Verify the error message
        self.assertIn("Failed to remove dataset", str(context.exception))
        self.assertIn(str(self.georef), str(context.exception))

        # Verify get_item was called
        self.mock_workspace.get_item.assert_called_once()

        # Verify delete_item was called
        self.mock_workspace.delete_item.assert_called_once()


if __name__ == "__main__":
    unittest.main()
