#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from enum import Enum, auto

import shapely

from aws.osml.geoagents.bedrock import CommonParameters, ToolExecutionError


class TestEnum(Enum):
    """Test enumeration for parse_enum_parameter tests."""

    RED = auto()
    GREEN = auto()
    BLUE = auto()


class TestCommonParameters(unittest.TestCase):
    """Test cases for the CommonParameters utility class."""

    def test_parse_dataset_georef_valid_wkt(self):
        """Test parsing valid WKT string as GeoDataReference."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "dataset", "value": "POINT (0 0)", "type": "string"}],
        }

        georef = CommonParameters.parse_dataset_georef(event)
        self.assertIsNotNone(georef)
        self.assertEqual(georef.reference_string, "POINT (0 0)")
        self.assertTrue(georef.is_wkt())

    def test_parse_dataset_georef_valid_file_path(self):
        """Test parsing valid file path as GeoDataReference."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "dataset", "value": "/path/to/file.geojson", "type": "string"}],
        }

        georef = CommonParameters.parse_dataset_georef(event)
        self.assertIsNotNone(georef)
        self.assertEqual(georef.reference_string, "/path/to/file.geojson")
        self.assertTrue(georef.is_file_path())

    def test_parse_dataset_georef_valid_stac(self):
        """Test parsing valid STAC reference as GeoDataReference."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "dataset", "value": "stac:test-dataset", "type": "string"}],
        }

        georef = CommonParameters.parse_dataset_georef(event)
        self.assertIsNotNone(georef)
        self.assertEqual(georef.reference_string, "stac:test-dataset")
        self.assertTrue(georef.is_stac_reference())

    def test_parse_dataset_georef_invalid_wkt(self):
        """Test parsing invalid WKT string raises error regardless of is_required."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "dataset", "value": "POINT (invalid coordinates)", "type": "string"}],
        }

        # Should raise error even when parameter is optional
        with self.assertRaises(ToolExecutionError) as context:
            CommonParameters.parse_dataset_georef(event, is_required=False)
        self.assertIn("Unable to construct a valid geo data reference", str(context.exception))

        # Should raise error when parameter is required
        with self.assertRaises(ToolExecutionError) as context:
            CommonParameters.parse_dataset_georef(event, is_required=True)
        self.assertIn("Unable to construct a valid geo data reference", str(context.exception))

    def test_parse_dataset_georef_invalid_type(self):
        """Test parsing non-string value raises error."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "dataset", "value": {"invalid": "type"}, "type": "object"}],
        }

        with self.assertRaises(ToolExecutionError) as context:
            CommonParameters.parse_dataset_georef(event)
        self.assertIn("Unable to construct a valid geo data reference", str(context.exception))

    def test_parse_dataset_georef_custom_param_name(self):
        """Test parsing GeoDataReference with custom parameter name."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "custom_dataset", "value": "POINT (1 1)", "type": "string"}],
        }

        georef = CommonParameters.parse_dataset_georef(event, param_name="custom_dataset")
        self.assertIsNotNone(georef)
        self.assertEqual(georef.reference_string, "POINT (1 1)")

    def test_parse_dataset_georef_missing_required(self):
        """Test handling of missing required parameter."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [],
        }

        with self.assertRaises(ToolExecutionError) as context:
            CommonParameters.parse_dataset_georef(event, is_required=True)
        self.assertIn("Missing required parameter", str(context.exception))

    def test_parse_dataset_georef_missing_optional(self):
        """Test handling of missing optional parameter."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [],
        }

        result = CommonParameters.parse_dataset_georef(event, is_required=False)
        self.assertIsNone(result)

    def test_parse_shape_parameter_valid(self):
        """Test parsing valid WKT string."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "filter", "value": "POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))", "type": "string"}],
        }

        shape = CommonParameters.parse_shape_parameter(event)
        self.assertIsNotNone(shape)
        self.assertTrue(shapely.is_valid(shape))
        self.assertEqual(shape.geom_type, "Polygon")

    def test_parse_shape_parameter_invalid_string(self):
        """Test parsing invalid WKT string raises error regardless of is_required."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "filter", "value": "NOT A WKT STRING", "type": "string"}],
        }

        # Should raise error even when parameter is optional
        with self.assertRaises(ToolExecutionError) as context:
            CommonParameters.parse_shape_parameter(event, is_required=False)
        self.assertIn("Unable to parse", str(context.exception))

        # Should raise error when parameter is required
        with self.assertRaises(ToolExecutionError) as context:
            CommonParameters.parse_shape_parameter(event, is_required=True)
        self.assertIn("Unable to parse", str(context.exception))

    def test_parse_shape_parameter_invalid_type(self):
        """Test parsing non-string value raises error."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "filter", "value": {"invalid": "type"}, "type": "object"}],
        }

        with self.assertRaises(ToolExecutionError) as context:
            CommonParameters.parse_shape_parameter(event)
        self.assertIn("Unable to parse", str(context.exception))

    def test_parse_shape_parameter_custom_param_name(self):
        """Test parsing shape with custom parameter name."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "custom_shape", "value": "POINT (0 0)", "type": "string"}],
        }

        shape = CommonParameters.parse_shape_parameter(event, param_name="custom_shape")
        self.assertIsNotNone(shape)
        self.assertTrue(shapely.is_valid(shape))
        self.assertEqual(shape.geom_type, "Point")

    def test_parse_shape_parameter_missing_required(self):
        """Test handling of missing required parameter."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [],
        }

        with self.assertRaises(ToolExecutionError) as context:
            CommonParameters.parse_shape_parameter(event, is_required=True)
        self.assertIn("Missing required parameter", str(context.exception))

    def test_parse_shape_parameter_missing_optional(self):
        """Test handling of missing optional parameter."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [],
        }

        result = CommonParameters.parse_shape_parameter(event, is_required=False)
        self.assertIsNone(result)

    def test_parse_distance_valid(self):
        """Test parsing valid positive number."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "distance", "value": "100.5", "type": "string"}],
        }

        distance = CommonParameters.parse_distance(event)
        self.assertEqual(distance, 100.5)

    def test_parse_distance_invalid_string(self):
        """Test parsing invalid string raises error regardless of is_required."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "distance", "value": "not a number", "type": "string"}],
        }

        # Should raise error even when parameter is optional
        with self.assertRaises(ToolExecutionError) as context:
            CommonParameters.parse_distance(event, is_required=False)
        self.assertIn("Unable to parse", str(context.exception))

        # Should raise error when parameter is required
        with self.assertRaises(ToolExecutionError) as context:
            CommonParameters.parse_distance(event, is_required=True)
        self.assertIn("Unable to parse", str(context.exception))

    def test_parse_distance_negative(self):
        """Test parsing negative number raises error."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "distance", "value": "-10", "type": "string"}],
        }

        with self.assertRaises(ToolExecutionError) as context:
            CommonParameters.parse_distance(event)
        self.assertIn("Unable to parse", str(context.exception))

    def test_parse_distance_custom_param_name(self):
        """Test parsing distance with custom parameter name."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "custom_distance", "value": "50", "type": "string"}],
        }

        distance = CommonParameters.parse_distance(event, param_name="custom_distance")
        self.assertEqual(distance, 50.0)

    def test_parse_distance_missing_required(self):
        """Test handling of missing required parameter."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [],
        }

        with self.assertRaises(ToolExecutionError) as context:
            CommonParameters.parse_distance(event, is_required=True)
        self.assertIn("Missing required parameter", str(context.exception))

    def test_parse_distance_missing_optional(self):
        """Test handling of missing optional parameter."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [],
        }

        result = CommonParameters.parse_distance(event, is_required=False)
        self.assertIsNone(result)

    def test_parse_enum_parameter_valid(self):
        """Test parsing valid enum value."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "color", "value": "RED", "type": "string"}],
        }

        enum_value = CommonParameters.parse_enum_parameter(event, TestEnum, "color")
        self.assertEqual(enum_value, TestEnum.RED)

    def test_parse_enum_parameter_case_insensitive(self):
        """Test parsing enum value is case-insensitive."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "color", "value": "blue", "type": "string"}],
        }

        enum_value = CommonParameters.parse_enum_parameter(event, TestEnum, "color")
        self.assertEqual(enum_value, TestEnum.BLUE)

    def test_parse_enum_parameter_invalid_value(self):
        """Test parsing invalid enum value raises error regardless of is_required."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "color", "value": "YELLOW", "type": "string"}],
        }

        # Should raise error even when parameter is optional
        with self.assertRaises(ToolExecutionError) as context:
            CommonParameters.parse_enum_parameter(event, TestEnum, "color", is_required=False)
        self.assertIn("Unable to parse", str(context.exception))

        # Should raise error when parameter is required
        with self.assertRaises(ToolExecutionError) as context:
            CommonParameters.parse_enum_parameter(event, TestEnum, "color", is_required=True)
        self.assertIn("Unable to parse", str(context.exception))

    def test_parse_enum_parameter_invalid_type(self):
        """Test parsing non-string value raises error."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "color", "value": {"invalid": "type"}, "type": "object"}],
        }

        with self.assertRaises(ToolExecutionError) as context:
            CommonParameters.parse_enum_parameter(event, TestEnum, "color")
        self.assertIn("Unable to parse", str(context.exception))

    def test_parse_enum_parameter_invalid_enum_class(self):
        """Test providing invalid enum_class raises error."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "color", "value": "RED", "type": "string"}],
        }

        with self.assertRaises(ToolExecutionError) as context:
            CommonParameters.parse_enum_parameter(event, str, "color")  # type: ignore
        self.assertIn("Invalid enum_class parameter", str(context.exception))

    def test_parse_enum_parameter_custom_param_name(self):
        """Test parsing enum with custom parameter name."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "custom_color", "value": "GREEN", "type": "string"}],
        }

        enum_value = CommonParameters.parse_enum_parameter(event, TestEnum, "custom_color")
        self.assertEqual(enum_value, TestEnum.GREEN)

    def test_parse_enum_parameter_missing_required(self):
        """Test handling of missing required parameter."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [],
        }

        with self.assertRaises(ToolExecutionError) as context:
            CommonParameters.parse_enum_parameter(event, TestEnum, "color", is_required=True)
        self.assertIn("Missing required parameter", str(context.exception))

    def test_parse_enum_parameter_missing_optional(self):
        """Test handling of missing optional parameter."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [],
        }

        result = CommonParameters.parse_enum_parameter(event, TestEnum, "color", is_required=False)
        self.assertIsNone(result)

    def test_parse_string_parameter_valid(self):
        """Test parsing valid string."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "text", "value": "Hello World", "type": "string"}],
        }

        text = CommonParameters.parse_string_parameter(event, "text")
        self.assertEqual(text, "Hello World")

    def test_parse_string_parameter_non_string_value(self):
        """Test parsing non-string value is converted to string."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "text", "value": 42, "type": "number"}],
        }

        text = CommonParameters.parse_string_parameter(event, "text")
        self.assertEqual(text, "42")

    def test_parse_string_parameter_custom_param_name(self):
        """Test parsing string with custom parameter name."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "custom_text", "value": "Custom Value", "type": "string"}],
        }

        text = CommonParameters.parse_string_parameter(event, "custom_text")
        self.assertEqual(text, "Custom Value")

    def test_parse_string_parameter_missing_required(self):
        """Test handling of missing required parameter."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [],
        }

        with self.assertRaises(ToolExecutionError) as context:
            CommonParameters.parse_string_parameter(event, "text", is_required=True)
        self.assertIn("Missing required parameter", str(context.exception))

    def test_parse_string_parameter_missing_optional(self):
        """Test handling of missing optional parameter."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [],
        }

        result = CommonParameters.parse_string_parameter(event, "text", is_required=False)
        self.assertIsNone(result)

    def test_parse_numeric_parameter_valid_integer(self):
        """Test parsing valid integer."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "number", "value": "42", "type": "string"}],
        }

        number = CommonParameters.parse_numeric_parameter(event, "number")
        self.assertEqual(number, 42.0)

    def test_parse_numeric_parameter_valid_float(self):
        """Test parsing valid float."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "number", "value": "42.5", "type": "string"}],
        }

        number = CommonParameters.parse_numeric_parameter(event, "number")
        self.assertEqual(number, 42.5)

    def test_parse_numeric_parameter_invalid_string(self):
        """Test parsing invalid string raises error regardless of is_required."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "number", "value": "not a number", "type": "string"}],
        }

        # Should raise error even when parameter is optional
        with self.assertRaises(ToolExecutionError) as context:
            CommonParameters.parse_numeric_parameter(event, "number", is_required=False)
        self.assertIn("Unable to parse", str(context.exception))

        # Should raise error when parameter is required
        with self.assertRaises(ToolExecutionError) as context:
            CommonParameters.parse_numeric_parameter(event, "number", is_required=True)
        self.assertIn("Unable to parse", str(context.exception))

    def test_parse_numeric_parameter_negative_when_positive_required(self):
        """Test parsing negative number when must_be_positive is True raises error."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "number", "value": "-10", "type": "string"}],
        }

        with self.assertRaises(ToolExecutionError) as context:
            CommonParameters.parse_numeric_parameter(event, "number", must_be_positive=True)
        self.assertIn("must be a valid positive number", str(context.exception))

    def test_parse_numeric_parameter_negative_when_positive_not_required(self):
        """Test parsing negative number when must_be_positive is False succeeds."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "number", "value": "-10", "type": "string"}],
        }

        number = CommonParameters.parse_numeric_parameter(event, "number", must_be_positive=False)
        self.assertEqual(number, -10.0)

    def test_parse_numeric_parameter_custom_param_name(self):
        """Test parsing number with custom parameter name."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "custom_number", "value": "50", "type": "string"}],
        }

        number = CommonParameters.parse_numeric_parameter(event, "custom_number")
        self.assertEqual(number, 50.0)

    def test_parse_numeric_parameter_missing_required(self):
        """Test handling of missing required parameter."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [],
        }

        with self.assertRaises(ToolExecutionError) as context:
            CommonParameters.parse_numeric_parameter(event, "number", is_required=True)
        self.assertIn("Missing required parameter", str(context.exception))

    def test_parse_numeric_parameter_missing_optional(self):
        """Test handling of missing optional parameter."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [],
        }

        result = CommonParameters.parse_numeric_parameter(event, "number", is_required=False)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
