#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest

import shapely

from aws.osml.geoagents.spatial.buffer_operation import buffer_operation


class TestBufferOperation(unittest.TestCase):
    def test_buffer_operation_successful(self):
        """Test successful buffering of a geometry."""
        # Create a test point
        point = shapely.from_wkt("POINT(0 0)")

        # Call the operation function
        result = buffer_operation(point, 1000)

        # Verify the result contains expected text
        self.assertIn("has been buffered by 1000", result)
        self.assertIn("POLYGON ((", result)

    def test_buffer_operation_with_complex_geometry(self):
        """Test buffering with a more complex geometry."""
        # Create a polygon
        polygon = shapely.from_wkt("POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))")

        # Call the operation function
        result = buffer_operation(polygon, 500)

        # Verify the result contains expected text
        self.assertIn("has been buffered by 500", result)
        self.assertIn("POLYGON ((", result)

    def test_buffer_operation_with_zero_distance(self):
        """Test buffering with zero distance."""
        # Create a test point
        point = shapely.from_wkt("POINT(0 0)")

        # Call the operation function with zero distance
        result = buffer_operation(point, 0)

        # Verify the result contains expected text
        self.assertIn("must be at least 1", result)


if __name__ == "__main__":
    unittest.main()
