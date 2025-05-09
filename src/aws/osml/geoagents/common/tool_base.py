#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import json
from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple

from .workspace import Workspace


class ToolExecutionError(Exception):
    """
    Exception class for errors that will pass specific information back to the
    LLM orchestrator.
    """

    def __init__(self, message: str):
        """
        Construct an exception with a message that should be passed on to the LLM
        orchestrator invoking this tool. The message should have enough information
        so the orchestrator can diagnose and correct an error if it is a problem
        that can be fixed by altering parameters.

        :param message: a natural language error message describing the issue
        """
        self.message = message
        super().__init__(self.message)


class ToolBase(ABC):
    """
    This is the base class for all the geoagent tools defined in this package. It
    defines common attributes and generic utility functions that are not unique to
    any specific geospatial operation.
    """

    def __init__(self, action_group: str, function_name):
        """
        Construct the tool recording the action group and name.

        :param action_group: the group of actions this tool falls inside
        :param function_name: the name of this geospatial operation
        """
        self._action_group = action_group
        self._function_name = function_name

    @property
    def action_group(self) -> str:
        """Get the action group associated with this tool."""
        return self._action_group

    @property
    def function_name(self) -> str:
        """Get the name of the geospatial operation."""
        return self._function_name

    @abstractmethod
    def handler(self, event: dict[str, Any], context: dict[str, Any], workspace: Workspace) -> dict[str, Any]:
        """
        This is the common interface that will be invoked whenever a tool receives a
        Lambda input event from Bedrock. The expectation is that this handler will
        perform any necessary calculations and then return response that conforms to
        the Bedrock API. A workspace for this user session is also provided to help tools
        share geospatial assets that are too big to exchange through the LLM context.

        The structure for the input Bedrock event is defined here:
        https://docs.aws.amazon.com/bedrock/latest/userguide/agents-lambda.html#agents-lambda-input
        A private utility method _get_parameter_info() has been provided to help implementers
        extract any parameters defined when registering this tool with a Bedrock Action Group.

        The expected response structure is defined here:
        https://docs.aws.amazon.com/bedrock/latest/userguide/agents-lambda.html#agents-lambda-response
        Note that a private utility method _create_action_response(...) has been provided to
        create this result structure given the TEXT response body. TEXT is the only contentType
        currently supported by Bedrock agents.

        Any additional information about the Lambda function or execution environment is passed
        as the context structure. That information is not specific to Bedrock and can be viewed
        here: https://docs.aws.amazon.com/lambda/latest/dg/python-context.html

        :param event: the Lambda input event from Bedrock
        :param context: the Lambda context object for this handler
        :param workspace: the user workspace for storing large geospatial assets
        :raises ToolExecutionError: the tool was unable to process the event
        :return: the Lambda response structure for Bedrock
        """

    @staticmethod
    def get_parameter_info(event: dict[str, Any], parameter_name: str) -> Tuple[Optional[Any], Optional[str]]:
        """
        Utility function to extract the value and type of the named event parameter.

        :param event: the Lambda input event from Bedrock
        :param parameter_name: the name of the parameter to fetch
        :return: a tuple containing the parameter value and type or None, None if not found
        """
        parameters = event.get("parameters", [])
        for param in parameters:
            if param["name"] == parameter_name:
                return param["value"], param["type"]
        return None, None

    @staticmethod
    def create_action_response(event: dict[str, Any], result: str, is_error: bool = False) -> dict[str, Any]:
        """
        Utility function to encode a string result into the Bedrock Agent response structure.

        :param event: the Lambda input event from Bedrock
        :param result: the text to include in the response body
        :param is_error: true if this response message should be flagged as an error
        :return: the Bedrock Agent response structure
        """
        body_property_name = "result"
        if is_error:
            body_property_name = "error"

        response_body = {"TEXT": {"body": json.dumps({body_property_name: result})}}
        action_response = {
            "actionGroup": event.get("actionGroup", ""),
            "function": event.get("function", ""),
            "functionResponse": {"responseBody": response_body},
        }
        lambda_response = {"response": action_response, "messageVersion": event.get("messageVersion", "1.0")}
        return lambda_response

    @staticmethod
    def get_requesting_user(event: dict[str, Any]) -> str:
        """
        Get a unique user ID for this event.

        If a userId is included in the sessionAttributes we will use that which will give us the
        ability to persist information in the workspace across sessions (up to the retention value
        of the workspace). Placing a 'userId' attribute in the sessionAttributes is something a client
        must implement (i.e. it is not a Bedrock standard) so if it is missing we will default back to
        the `sessionId`. In that case the workspace contents will not be tied to a specific durable
        user but they will be available to future requests in the same conversation.

        :param event: the Lambda input event from Bedrock
        :return: the user ID
        """
        sessionAttributes = event.get("sessionAttributes", {})
        user_id = sessionAttributes.get("userId", None)
        if not user_id:
            user_id = event.get("sessionId")
        return user_id
