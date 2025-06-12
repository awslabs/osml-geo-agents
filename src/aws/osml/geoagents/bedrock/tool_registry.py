#  Copyright 2025 Amazon.com, Inc. or its affiliates.

from collections import defaultdict
from typing import Optional

from .tool_base import ToolBase


class ToolRegistry:
    """
    This registry manages a mapping of the action group and function names to
    classes that provide handlers for Bedrock action group events.

    TODO: Think about whether we should replace this registry with a more complex
          dependency injection or plugin framework that will automatically update
          when new tools are implemented.
    """

    def __init__(self):
        """Constructor for an empty registry."""
        self._tools: dict[str, ToolBase] = defaultdict(lambda: None)

    def register_tool(self, tool: ToolBase) -> None:
        """
        Add a new tool to the registry.

        :param tool: the tool to register
        :raises ValueError: if a tool with the same names is registered
        """
        tool_key = f"{tool.action_group}:{tool.function_name}"
        if tool_key in self._tools:
            raise ValueError(
                "Another tool has already been registered with this action " f"group and function name: {tool_key}"
            )
        self._tools[tool_key] = tool

    def find_tool(self, action_group: str, function_name: str) -> Optional[ToolBase]:
        """
        Returns the tool with the matching action_group and function name if it can be found.

        :param action_group: the name of the action group
        :param function_name: the name of the function within the action group
        :return: the tool registered with this action_group and function_name
        """
        tool_key = f"{action_group}:{function_name}"
        return self._tools[tool_key]
