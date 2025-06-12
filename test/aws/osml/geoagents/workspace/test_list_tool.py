#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

from pystac import Item

from aws.osml.geoagents.bedrock import ToolExecutionError
from aws.osml.geoagents.common import Georeference, Workspace
from aws.osml.geoagents.workspace import ListTool


class TestListTool(unittest.TestCase):
    """Unit tests for the ListTool class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.tool = ListTool()
        self.mock_workspace = Mock(spec=Workspace)
        self.mock_workspace.session_local_path = Path("/tmp/osml-geo-agents/test")

        # Create a sample event
        self.event = {
            "agent": "test_agent",
            "actionGroup": "WorkspaceActions",
            "function": "LIST",
            "parameters": [],
        }

    def test_handler_with_items(self):
        """Test listing items when there are items in the workspace."""
        # Create sample georefs
        georef1 = Georeference.from_parts(item_id="item1")
        georef2 = Georeference.from_parts(item_id="item2")

        # Mock the list_items method to return the sample georefs
        self.mock_workspace.list_items = Mock(return_value=[georef1, georef2])

        # Create sample items to be returned by get_item
        item1 = Item(id="item1", geometry=None, bbox=None, datetime=datetime.now(), properties={"title": "Dataset 1"})
        item2 = Item(id="item2", geometry=None, bbox=None, datetime=datetime.now(), properties={"title": "Dataset 2"})

        # Mock the get_item method to return the sample items
        self.mock_workspace.get_item = Mock(side_effect=lambda georef: item1 if georef.item_id == "item1" else item2)

        # Call the handler
        result = self.tool.handler(self.event, {}, self.mock_workspace)

        # Verify the result
        self.assertIn("Datasets in the workspace:", str(result))
        self.assertIn(str(georef1), str(result))
        self.assertIn(str(georef2), str(result))
        self.assertIn("Dataset 1", str(result))
        self.assertIn("Dataset 2", str(result))

        # Verify list_items was called
        self.mock_workspace.list_items.assert_called_once()

        # Verify get_item was called for each georef
        self.assertEqual(self.mock_workspace.get_item.call_count, 2)

    def test_handler_no_items(self):
        """Test listing items when there are no items in the workspace."""
        # Mock the list_items method to return an empty list
        self.mock_workspace.list_items = Mock(return_value=[])

        # Call the handler
        result = self.tool.handler(self.event, {}, self.mock_workspace)

        # Verify the result
        self.assertIn("No datasets found", str(result))

        # Verify list_items was called
        self.mock_workspace.list_items.assert_called_once()

        # Verify get_item was not called
        self.mock_workspace.get_item.assert_not_called()

    def test_handler_get_item_error(self):
        """Test handling of errors when getting item details."""
        # Create sample georef
        georef = Georeference.from_parts(item_id="item1")

        # Mock the list_items method to return the sample georef
        self.mock_workspace.list_items = Mock(return_value=[georef])

        # Mock the get_item method to raise an exception
        self.mock_workspace.get_item = Mock(side_effect=Exception("Failed to get item"))

        # Call the handler
        result = self.tool.handler(self.event, {}, self.mock_workspace)

        # Verify the result still includes the georef even though get_item failed
        self.assertIn(str(georef), str(result))

        # Verify list_items was called
        self.mock_workspace.list_items.assert_called_once()

        # Verify get_item was called
        self.mock_workspace.get_item.assert_called_once()

    def test_handler_list_items_error(self):
        """Test handling of errors when listing items."""
        # Mock the list_items method to raise an exception
        self.mock_workspace.list_items = Mock(side_effect=Exception("Failed to list items"))

        # Call the handler and expect an exception
        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(self.event, {}, self.mock_workspace)

        # Verify the error message
        self.assertIn("Failed to list datasets", str(context.exception))


if __name__ == "__main__":
    unittest.main()
