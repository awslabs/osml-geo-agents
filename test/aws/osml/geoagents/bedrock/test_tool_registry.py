#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from collections import defaultdict

from aws.osml.geoagents.bedrock import ToolBase, ToolRegistry


class MockTool(ToolBase):
    """Mock implementation of ToolBase for testing"""

    def __init__(self, action_group: str, function_name: str):
        super().__init__(action_group, function_name)

    def handler(self, event, context, workspace):
        return "mock_response"


class TestToolRegistry(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.registry = ToolRegistry()
        self.test_tool = MockTool("test_group", "test_function")

    def test_init(self):
        """Test initialization of ToolRegistry"""
        self.assertIsInstance(self.registry._tools, defaultdict)
        self.assertIsNone(self.registry._tools["nonexistent"])

    def test_register_tool(self):
        """Test registering a new tool"""
        self.registry.register_tool(self.test_tool)

        # Verify tool was registered
        tool_key = f"{self.test_tool.action_group}:{self.test_tool.function_name}"
        self.assertEqual(self.registry._tools[tool_key], self.test_tool)

    def test_register_duplicate_tool(self):
        """Test registering a tool with duplicate action group and function name"""
        # Register the first tool
        self.registry.register_tool(self.test_tool)

        # Try to register another tool with the same action group and function name
        duplicate_tool = MockTool("test_group", "test_function")

        with self.assertRaises(ValueError) as context:
            self.registry.register_tool(duplicate_tool)

        self.assertIn("Another tool has already been registered", str(context.exception))

    def test_find_tool_existing(self):
        """Test finding an existing tool"""
        # Register a tool
        self.registry.register_tool(self.test_tool)

        # Find the tool
        found_tool = self.registry.find_tool("test_group", "test_function")

        self.assertEqual(found_tool, self.test_tool)

    def test_find_tool_nonexistent(self):
        """Test finding a non-existent tool"""
        # Try to find a tool that hasn't been registered
        found_tool = self.registry.find_tool("nonexistent_group", "nonexistent_function")

        self.assertIsNone(found_tool)

    def test_find_tool_after_multiple_registrations(self):
        """Test finding tools after registering multiple tools"""
        # Create and register multiple tools
        tool1 = MockTool("group1", "function1")
        tool2 = MockTool("group2", "function2")

        self.registry.register_tool(tool1)
        self.registry.register_tool(tool2)

        # Find each tool
        found_tool1 = self.registry.find_tool("group1", "function1")
        found_tool2 = self.registry.find_tool("group2", "function2")

        self.assertEqual(found_tool1, tool1)
        self.assertEqual(found_tool2, tool2)


if __name__ == "__main__":
    unittest.main()
