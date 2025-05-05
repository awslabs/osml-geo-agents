#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import json
import unittest

from aws.osml.geoagents.common import ToolBase


class TestTool(ToolBase):
    """Concrete implementation of ToolBase for testing"""

    def __init__(self):
        super().__init__("test_group", "test_function")

    def handler(self, event, context, workspace):
        return "test_response"


class TestToolBase(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.tool = TestTool()

        # Sample event structure following Bedrock Agent documentation
        self.test_event = {
            "messageVersion": "1.0",
            "agent": "test-agent",
            "actionGroup": "test_group",
            "function": "test_function",
            "parameters": [
                {"name": "param1", "type": "string", "value": "test_value"},
                {"name": "param2", "type": "number", "value": 42},
            ],
        }

    def test_get_parameter_info_existing_parameter(self):
        """Test _get_parameter_info with an existing parameter"""
        value, param_type = self.tool.get_parameter_info(self.test_event, "param1")
        self.assertEqual(value, "test_value")
        self.assertEqual(param_type, "string")

        value, param_type = self.tool.get_parameter_info(self.test_event, "param2")
        self.assertEqual(value, 42)
        self.assertEqual(param_type, "number")

    def test_get_parameter_info_nonexistent_parameter(self):
        """Test _get_parameter_info with a non-existent parameter"""
        value, param_type = self.tool.get_parameter_info(self.test_event, "nonexistent")
        self.assertIsNone(value)
        self.assertIsNone(param_type)

    def test_get_parameter_info_empty_parameters(self):
        """Test _get_parameter_info with empty parameters list"""
        event_without_params = self.test_event.copy()
        event_without_params["parameters"] = []
        value, param_type = self.tool.get_parameter_info(event_without_params, "param1")
        self.assertIsNone(value)
        self.assertIsNone(param_type)

    def test_create_action_response_success(self):
        """Test _create_action_response for successful response"""
        result = "Operation completed successfully"
        response = self.tool.create_action_response(self.test_event, result)

        # Verify response structure
        self.assertIn("response", response)
        self.assertIn("messageVersion", response)
        self.assertEqual(response["messageVersion"], "1.0")

        # Verify action response
        action_response = response["response"]
        self.assertEqual(action_response["actionGroup"], "test_group")
        self.assertEqual(action_response["function"], "test_function")

        # Verify response body
        function_response = action_response["functionResponse"]
        self.assertIn("responseBody", function_response)
        self.assertIn("TEXT", function_response["responseBody"])

        # Verify the result is properly encoded in the body
        body = json.loads(function_response["responseBody"]["TEXT"]["body"])
        self.assertIn("result", body)
        self.assertEqual(body["result"], result)

    def test_create_action_response_error(self):
        """Test _create_action_response for error response"""
        error_message = "An error occurred"
        response = self.tool.create_action_response(self.test_event, error_message, is_error=True)

        # Verify response structure
        self.assertIn("response", response)
        self.assertIn("messageVersion", response)

        # Verify action response
        action_response = response["response"]
        self.assertEqual(action_response["actionGroup"], "test_group")
        self.assertEqual(action_response["function"], "test_function")

        # Verify error response body
        function_response = action_response["functionResponse"]
        self.assertIn("responseBody", function_response)
        self.assertIn("TEXT", function_response["responseBody"])

        # Verify the error is properly encoded in the body
        body = json.loads(function_response["responseBody"]["TEXT"]["body"])
        self.assertIn("error", body)
        self.assertEqual(body["error"], error_message)

    def test_create_action_response_minimal_event(self):
        """Test _create_action_response with minimal event structure"""
        minimal_event = {}
        result = "Test result"
        response = self.tool.create_action_response(minimal_event, result)

        # Verify response structure with default values
        self.assertIn("response", response)
        self.assertIn("messageVersion", response)
        self.assertEqual(response["messageVersion"], "1.0")

        # Verify action response with empty values
        action_response = response["response"]
        self.assertEqual(action_response["actionGroup"], "")
        self.assertEqual(action_response["function"], "")

    def test_get_requesting_user_with_user_id(self):
        """Test get_requesting_user when userId is present in sessionAttributes"""
        event = {"sessionAttributes": {"userId": "test-user-123"}, "sessionId": "session-456"}
        user_id = self.tool.get_requesting_user(event)
        self.assertEqual(user_id, "test-user-123")

    def test_get_requesting_user_fallback_to_session_id(self):
        """Test get_requesting_user falls back to sessionId when userId is not present"""
        event = {"sessionAttributes": {}, "sessionId": "session-456"}
        user_id = self.tool.get_requesting_user(event)
        self.assertEqual(user_id, "session-456")

    def test_get_requesting_user_no_session_attributes(self):
        """Test get_requesting_user when sessionAttributes is missing"""
        event = {"sessionId": "session-789"}
        user_id = self.tool.get_requesting_user(event)
        self.assertEqual(user_id, "session-789")

    def test_get_requesting_user_empty_user_id(self):
        """Test get_requesting_user when userId is empty string"""
        event = {"sessionAttributes": {"userId": ""}, "sessionId": "session-456"}
        user_id = self.tool.get_requesting_user(event)
        self.assertEqual(user_id, "session-456")


if __name__ == "__main__":
    unittest.main()
