#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest

import shapely

from aws.osml.geoagents.spatial.translate_operation import translate_operation


class TestTranslateOperation(unittest.TestCase):
    def test_translate_operation_successful(self):
        """Test successful translation of a geometry."""
        # Create a test point
        point = shapely.from_wkt("POINT(0 0)")

        # Call the operation function
        result = translate_operation(point, 1000, 90)

        # Verify the result contains expected text
        self.assertIn("has been translated by 1000", result)
        self.assertIn("at heading 90 degrees", result)
        self.assertIn("POINT (", result)

    def test_translate_operation_with_complex_geometry(self):
        """Test translation with a more complex geometry."""
        # Create a polygon
        polygon = shapely.from_wkt("POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))")

        # Call the operation function
        result = translate_operation(polygon, 500, 45)

        # Verify the result contains expected text
        self.assertIn("has been translated by 500", result)
        self.assertIn("at heading 45 degrees", result)
        self.assertIn("POLYGON ((", result)

    def test_translate_operation_with_invalid_parameters(self):
        """Test translation with invalid heading."""
        # Create a test point
        point = shapely.from_wkt("POINT(0 0)")

        # Call the operation function with invalid heading
        with self.assertRaises(ValueError):
            translate_operation(point, 1000, -10)

        with self.assertRaises(ValueError):
            translate_operation(point, 1000, 360)

        with self.assertRaises(ValueError):
            translate_operation(point, 1000, None)

        with self.assertRaises(ValueError):
            translate_operation(None, 1000, 20)

        with self.assertRaises(ValueError):
            translate_operation(point, -10, 42)


if __name__ == "__main__":
    unittest.main()
