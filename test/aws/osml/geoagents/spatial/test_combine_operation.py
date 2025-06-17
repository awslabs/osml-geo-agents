#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest

import shapely

from aws.osml.geoagents.spatial.combine_operation import combine_operation


class TestCombineOperation(unittest.TestCase):
    def test_union_operation_successful(self):
        """Test successful union of two geometries."""
        # Create test geometries
        geometry1 = shapely.from_wkt("POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))")
        geometry2 = shapely.from_wkt("POLYGON((0.5 0.5, 1.5 0.5, 1.5 1.5, 0.5 1.5, 0.5 0.5))")

        # Call the operation function
        result = combine_operation(geometry1, geometry2, "union")

        # Verify the result contains expected text
        self.assertIn("union of the input geometries", result)
        self.assertIn("POLYGON", result)

    def test_intersection_operation_successful(self):
        """Test successful intersection of two geometries."""
        # Create test geometries
        geometry1 = shapely.from_wkt("POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))")
        geometry2 = shapely.from_wkt("POLYGON((0.5 0.5, 1.5 0.5, 1.5 1.5, 0.5 1.5, 0.5 0.5))")

        # Call the operation function
        result = combine_operation(geometry1, geometry2, "intersection")

        # Verify the result contains expected text
        self.assertIn("intersection of the input geometries", result)
        self.assertIn("POLYGON", result)

    def test_difference_operation_successful(self):
        """Test successful difference of two geometries."""
        # Create test geometries
        geometry1 = shapely.from_wkt("POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))")
        geometry2 = shapely.from_wkt("POLYGON((0.5 0.5, 1.5 0.5, 1.5 1.5, 0.5 1.5, 0.5 0.5))")

        # Call the operation function
        result = combine_operation(geometry1, geometry2, "difference")

        # Verify the result contains expected text
        self.assertIn("difference of the input geometries", result)
        self.assertIn("POLYGON", result)

    def test_combine_operation_with_invalid_operation_type(self):
        """Test combine operation with invalid operation type."""
        # Create test geometries
        geometry1 = shapely.from_wkt("POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))")
        geometry2 = shapely.from_wkt("POLYGON((0.5 0.5, 1.5 0.5, 1.5 1.5, 0.5 1.5, 0.5 0.5))")

        # Call the operation function with invalid operation type
        with self.assertRaises(ValueError):
            combine_operation(geometry1, geometry2, "invalid_operation")

    def test_combine_operation_with_invalid_parameters(self):
        """Test combine operation with invalid parameters."""
        # Create test geometries
        geometry1 = shapely.from_wkt("POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))")
        geometry2 = shapely.from_wkt("POLYGON((0.5 0.5, 1.5 0.5, 1.5 1.5, 0.5 1.5, 0.5 0.5))")

        # Call the operation function with invalid parameters
        with self.assertRaises(ValueError):
            combine_operation(None, geometry2, "union")

        with self.assertRaises(ValueError):
            combine_operation(geometry1, None, "union")

        with self.assertRaises(ValueError):
            combine_operation(None, None, "union")


if __name__ == "__main__":
    unittest.main()
