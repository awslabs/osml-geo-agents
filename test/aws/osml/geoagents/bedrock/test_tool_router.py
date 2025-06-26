#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import json
import unittest
from unittest.mock import Mock, patch

from aws.osml.geoagents.bedrock import ToolBase, ToolRegistry, ToolRouter
from aws.osml.geoagents.common import Workspace


class TestToolRouter(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.tool_registry = ToolRegistry()
        self.workspace_bucket = "XXXXXXXXXXX"
        self.workspace_cache = "/tmp/test-cache"
        self.tool_router = ToolRouter(
            tool_registry=self.tool_registry,
            workspace_bucket_name=self.workspace_bucket,
            workspace_local_cache=self.workspace_cache,
        )

    @patch("aws.osml.geoagents.bedrock.tool_router.Workspace")
    def test_successful_request_handling(self, mock_workspace_class):
        """Test successful handling of a valid request."""
        # Setup mock workspace
        mock_workspace = Mock(spec=Workspace)
        mock_workspace_class.return_value = mock_workspace

        # Create a mock tool
        mock_tool = Mock(spec=ToolBase)
        mock_tool.handler.return_value = {"status": "success"}

        # Register the mock tool
        self.tool_registry._tools["test_group:test_function"] = mock_tool

        # Create test event
        test_event = {
            "agent": "test_agent",
            "actionGroup": "test_group",
            "function": "test_function",
            "parameters": [],
            "sessionId": "test-session",
            "messageVersion": "1.0",
        }
        test_context = {}

        # Execute the request
        response = self.tool_router.handle_request(test_event, test_context)

        # Verify workspace creation
        mock_workspace_class.assert_called_once()

        # Verify the tool was called with correct arguments
        mock_tool.handler.assert_called_once_with(test_event, test_context, mock_workspace)

        # Verify response
        self.assertEqual(response, {"status": "success"})

    def test_error_handling_invalid_tool(self):
        """Test handling of requests for non-existent tools."""
        test_event = {
            "agent": "test_agent",
            "actionGroup": "invalid_group",
            "function": "invalid_function",
            "sessionId": "test-session",
            "messageVersion": "1.0",
        }
        test_context = {}

        response = self.tool_router.handle_request(test_event, test_context)

        # Verify error response structure
        self.assertIn("response", response)
        self.assertIn("messageVersion", response)
        self.assertEqual(response["messageVersion"], "1.0")

        action_response = response["response"]
        self.assertEqual(action_response["actionGroup"], "invalid_group")
        self.assertEqual(action_response["function"], "invalid_function")

        # Verify error message
        function_response = action_response["functionResponse"]
        self.assertIn("responseBody", function_response)
        self.assertIn("TEXT", function_response["responseBody"])

        error_body = json.loads(function_response["responseBody"]["TEXT"]["body"])
        self.assertIn("error", error_body)
        self.assertIn("Unknown action group or function", error_body["error"])

    @patch("aws.osml.geoagents.bedrock.tool_router.Workspace")
    def test_tool_exception_handling(self, mock_workspace_class):
        """Test handling of exceptions thrown by tools."""
        # Setup mock workspace
        mock_workspace = Mock(spec=Workspace)
        mock_workspace_class.return_value = mock_workspace

        # Create a mock tool that raises an exception
        mock_tool = Mock(spec=ToolBase)
        mock_tool.handler.side_effect = Exception("Tool execution failed")

        # Register the mock tool
        self.tool_registry._tools["test_group:test_function"] = mock_tool

        # Create test event
        test_event = {
            "agent": "test_agent",
            "actionGroup": "test_group",
            "function": "test_function",
            "sessionId": "test-session",
            "messageVersion": "1.0",
        }
        test_context = {}

        # Execute the request
        response = self.tool_router.handle_request(test_event, test_context)

        # Verify error response
        self.assertIn("response", response)
        action_response = response["response"]
        function_response = action_response["functionResponse"]
        error_body = json.loads(function_response["responseBody"]["TEXT"]["body"])
        self.assertIn("error", error_body)
        self.assertEqual(error_body["error"], "Tool execution failed")


if __name__ == "__main__":
    unittest.main()
