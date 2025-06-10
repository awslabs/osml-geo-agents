#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from unittest.mock import Mock, patch

import shapely

from aws.osml.geoagents.common import ToolExecutionError, Workspace
from aws.osml.geoagents.spatial.buffer_tool import BufferTool


class TestBufferTool(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.handler = BufferTool()
        self.mock_workspace = Mock(spec=Workspace)

        # Create a sample event with a point geometry and distance
        self.event = {
            "agent": "test_agent",
            "actionGroup": "SpatialReasoning",
            "function": "BUFFER",
            "parameters": [
                {"name": "geometry", "value": "POINT(0 0)", "type": "string"},
                {"name": "distance", "value": "100", "type": "string"},
            ],
        }

    @patch("aws.osml.geoagents.spatial.buffer_tool.buffer_geometry")
    def test_handler_successful_buffer(self, mock_buffer_geometry):
        """Test successful buffering of a geometry."""
        # Setup mock buffer_geometry
        mock_buffer_result = shapely.geometry.Point(0, 0).buffer(100)
        mock_buffer_geometry.return_value = mock_buffer_result

        # Call the handler
        result = self.handler.handler(self.event, None, self.mock_workspace)

        # Verify the result
        self.assertIn("has been buffered by 100", str(result))
        self.assertIn("POLYGON", str(result))

        # Verify buffer_geometry was called with correct parameters
        mock_buffer_geometry.assert_called_once()
        args, _ = mock_buffer_geometry.call_args
        self.assertEqual(args[1], 100.0)  # Check distance parameter

    def test_missing_required_parameters(self):
        """Test error handling when required parameters are missing."""
        # Test missing geometry
        event_missing_geometry = {
            "agent": "test_agent",
            "actionGroup": "SpatialReasoning",
            "function": "BUFFER",
            "parameters": [
                {"name": "distance", "value": "100", "type": "string"},
            ],
        }
        with self.assertRaises(ToolExecutionError):
            self.handler.handler(event_missing_geometry, None, self.mock_workspace)

        # Test missing distance
        event_missing_distance = {
            "agent": "test_agent",
            "actionGroup": "SpatialReasoning",
            "function": "BUFFER",
            "parameters": [
                {"name": "geometry", "value": "POINT(0 0)", "type": "string"},
            ],
        }
        with self.assertRaises(ToolExecutionError):
            self.handler.handler(event_missing_distance, None, self.mock_workspace)


if __name__ == "__main__":
    unittest.main()
