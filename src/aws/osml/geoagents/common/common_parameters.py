#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
from enum import Enum
from typing import Any, Optional

import shapely

from .georeference import Georeference
from .tool_base import ToolBase, ToolExecutionError

logger = logging.getLogger(__name__)


class CommonParameters:
    """
    A utility class that provides methods to parse and validate common parameter types
    used across multiple tools.
    """

    @staticmethod
    def parse_shape_parameter(
        event: dict[str, Any], param_name: str = "filter", is_required: bool = True
    ) -> Optional[shapely.Geometry]:
        """
        Parse a shape parameter as a WKT string and return a shapely geometry.

        :param event: the Lambda input event from Bedrock
        :param param_name: name of the parameter to parse (defaults to "filter")
        :param is_required: whether the parameter is required (defaults to True)
        :raises ToolExecutionError: if a required parameter is missing or if a provided value cannot be parsed
        :return: the parsed shapely geometry (never None if is_required=True, as it would raise ToolExecutionError instead)
        """
        shape_value, _ = ToolBase.get_parameter_info(event, param_name)

        # Handle missing parameter
        if shape_value is None:
            if is_required:
                raise ToolExecutionError(
                    f"Missing required parameter: '{param_name}'. "
                    "The parameter must be provided and be a valid WKT (Well Known Text) string."
                )
            return None

        # If value is provided, always validate it regardless of is_required
        try:
            # Cast to str to satisfy type checker since get_parameter_info returns Any
            shape_value_str = str(shape_value)
            shape = shapely.from_wkt(shape_value_str)
            if not shapely.is_valid(shape):
                raise ValueError("Invalid shape: not a valid geometry.")
            return shape
        except Exception as e:
            logger.info(f"Unable to parse shape parameter: {shape_value}", e)
            raise ToolExecutionError(
                f"Unable to parse '{param_name}' parameter: {shape_value}. "
                "The parameter must be a valid WKT (Well Known Text) string."
            )

    @staticmethod
    def parse_distance(event: dict[str, Any], param_name: str = "distance", is_required: bool = False) -> Optional[float]:
        """
        Parse a distance parameter as a float.

        :param event: the Lambda input event from Bedrock
        :param param_name: name of the parameter to parse (defaults to "distance")
        :param is_required: whether the parameter is required (defaults to False)
        :raises ToolExecutionError: if a required parameter is missing or if a provided value cannot be parsed
        :return: the parsed distance (never None if is_required=True, as it would raise ToolExecutionError instead)
        """
        distance_value, _ = ToolBase.get_parameter_info(event, param_name)

        # Handle missing parameter
        if distance_value is None:
            if is_required:
                raise ToolExecutionError(
                    f"Missing required parameter: '{param_name}'. "
                    "The parameter must be provided and be a valid positive number."
                )
            return None

        # If value is provided, always validate it regardless of is_required
        try:
            # TODO: Handle distances using units other than meters. distance_value is already a string
            #       so we should be able to use a simple parsing of standard units markings to decide
            #       if we need to run a conversion.
            distance = float(distance_value)
            if distance < 0:
                raise ValueError("Distance cannot be negative")
            return distance
        except ValueError as ve:
            logger.info(f"Unable to parse distance parameter: {distance_value}", ve)
            raise ToolExecutionError(
                f"Unable to parse '{param_name}' parameter: {distance_value}. "
                "The parameter must be a valid positive number."
            )

    @staticmethod
    def parse_dataset_georef(
        event: dict[str, Any], param_name: str = "dataset", is_required: bool = True
    ) -> Optional[Georeference]:
        """
        Parse a dataset parameter as a georeference.

        :param event: the Lambda input event from Bedrock
        :param param_name: name of the parameter to parse (defaults to "dataset")
        :param is_required: whether the parameter is required (defaults to True)
        :raises ToolExecutionError: if a required parameter is missing or if a provided value cannot be parsed
        :return: the parsed georeference (never None if is_required=True, as it would raise ToolExecutionError instead)
        """
        dataset_value, _ = ToolBase.get_parameter_info(event, param_name)

        # Handle missing parameter
        if dataset_value is None:
            if is_required:
                raise ToolExecutionError(
                    f"Missing required parameter: '{param_name}'. "
                    "The parameter must be provided and be a valid georeference encoded as a string."
                )
            return None

        # If value is provided, always validate it regardless of is_required
        try:
            # Cast to str to satisfy type checker since get_parameter_info returns Any
            dataset_value_str = str(dataset_value)
            return Georeference(encoded_value=dataset_value_str)
        except (ValueError, TypeError) as e:
            logger.info(f"Unable to parse dataset georef: {dataset_value}", e)
            raise ToolExecutionError(
                f"Unable to construct a valid georeference from '{param_name}' parameter. "
                "The parameter must be a valid georeference encoded as a string."
            )

    @staticmethod
    def parse_string_parameter(event: dict[str, Any], param_name: str, is_required: bool = True) -> Optional[str]:
        """
        Parse a string parameter.

        :param event: the Lambda input event from Bedrock
        :param param_name: name of the parameter to parse
        :param is_required: whether the parameter is required (defaults to True)
        :raises ToolExecutionError: if a required parameter is missing or if a provided value cannot be parsed
        :return: the parsed string (never None if is_required=True, as it would raise ToolExecutionError instead)
        """
        string_value, _ = ToolBase.get_parameter_info(event, param_name)

        # Handle missing parameter
        if string_value is None:
            if is_required:
                raise ToolExecutionError(
                    f"Missing required parameter: '{param_name}'. " "The parameter must be provided and be a valid string."
                )
            return None

        # If value is provided, always validate it regardless of is_required
        try:
            return str(string_value)
        except Exception as e:
            logger.info(f"Unable to parse string parameter: {string_value}", e)
            raise ToolExecutionError(
                f"Unable to parse '{param_name}' parameter: {string_value}. " "The parameter must be a valid string."
            )

    @staticmethod
    def parse_enum_parameter(
        event: dict[str, Any], enum_class: type[Enum], param_name: str, is_required: bool = True
    ) -> Optional[Enum]:
        """
        Parse a string parameter as an enumeration value.

        :param event: the Lambda input event from Bedrock
        :param enum_class: the Enum class to parse the value into
        :param param_name: name of the parameter to parse
        :param is_required: whether the parameter is required (defaults to True)
        :raises ToolExecutionError: if a required parameter is missing, if a provided value cannot be parsed,
                                  or if enum_class is not an Enum type
        :return: the parsed enum value (never None if is_required=True, as it would raise ToolExecutionError instead)
        """
        # Validate enum_class is actually an Enum
        if not isinstance(enum_class, type) or not issubclass(enum_class, Enum):
            raise ToolExecutionError(
                f"Invalid enum_class parameter: {enum_class}. " "The parameter must be a valid Enum class."
            )

        enum_value, _ = ToolBase.get_parameter_info(event, param_name)

        # Handle missing parameter
        if enum_value is None:
            if is_required:
                raise ToolExecutionError(
                    f"Missing required parameter: '{param_name}'. "
                    f"The parameter must be provided and be one of: {[e.name for e in enum_class]}."
                )
            return None

        # If value is provided, always validate it regardless of is_required
        try:
            # Cast to str to satisfy type checker since get_parameter_info returns Any
            enum_value_str = str(enum_value).upper()
            return enum_class[enum_value_str]
        except KeyError as e:
            logger.info(f"Unable to parse enum parameter: {enum_value}", e)
            raise ToolExecutionError(
                f"Unable to parse '{param_name}' parameter: {enum_value}. "
                f"The parameter must be one of: {[e.name for e in enum_class]}."
            )
