#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from unittest.mock import Mock

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
                {"name": "distance", "value": "1000", "type": "string"},
            ],
        }

    def test_handler_successful_buffer(self):
        """Test successful buffering of a geometry."""
        # Call the handler with the actual event data
        result = self.handler.handler(self.event, None, self.mock_workspace)

        # Verify the result contains expected text
        self.assertIn("has been buffered by 1000", str(result))

        # Verify the result contains a valid polygon WKT
        self.assertIn("POLYGON ((", str(result))

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
