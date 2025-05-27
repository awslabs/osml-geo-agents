#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest

from aws.osml.geoagents.common.common_parameters import CommonParameters
from aws.osml.geoagents.common.tool_base import ToolExecutionError


class TestCommonParameters(unittest.TestCase):
    """Test cases for the CommonParameters utility class."""

    def test_parse_dataset_georef_valid(self):
        """Test parsing valid georeference."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "dataset", "value": "georef:test-dataset", "type": "string"}],
        }

        georef = CommonParameters.parse_dataset_georef(event)
        self.assertEqual(georef.encoded_value, "georef:test-dataset")

    def test_parse_dataset_georef_invalid_string(self):
        """Test parsing invalid georeference string raises error regardless of is_required."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "dataset", "value": "invalid:reference", "type": "string"}],
        }

        # Should raise error even when parameter is optional
        with self.assertRaises(ToolExecutionError) as context:
            CommonParameters.parse_dataset_georef(event, is_required=False)
        self.assertIn("Unable to construct a valid georeference", str(context.exception))

        # Should raise error when parameter is required
        with self.assertRaises(ToolExecutionError) as context:
            CommonParameters.parse_dataset_georef(event, is_required=True)
        self.assertIn("Unable to construct a valid georeference", str(context.exception))

    def test_parse_dataset_georef_invalid_type(self):
        """Test parsing non-string value raises error."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "dataset", "value": {"invalid": "type"}, "type": "object"}],
        }

        with self.assertRaises(ToolExecutionError) as context:
            CommonParameters.parse_dataset_georef(event)
        self.assertIn("Unable to construct a valid georeference", str(context.exception))

    def test_parse_dataset_georef_custom_param_name(self):
        """Test parsing georeference with custom parameter name."""
        event = {
            "actionGroup": "TestGroup",
            "function": "TEST",
            "parameters": [{"name": "custom_dataset", "value": "georef:test-dataset", "type": "string"}],
        }

        georef = CommonParameters.parse_dataset_georef(event, param_name="custom_dataset")
        self.assertEqual(georef.encoded_value, "georef:test-dataset")

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
        self.assertTrue(shape.is_valid)
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
        self.assertTrue(shape.is_valid)
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


if __name__ == "__main__":
    unittest.main()
