#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import time
import unittest

from aws.osml.geoagents.common.georeference import GEOREF_PROTOCOL, Georeference


class TestGeoreference(unittest.TestCase):
    def test_valid_initialization(self):
        """Test initialization with valid georeference strings"""
        # Test without asset tag
        georef = Georeference(f"{GEOREF_PROTOCOL}ABC123")
        self.assertEqual(georef.item_id, "ABC123")
        self.assertIsNone(georef.asset_tag)

        # Test with asset tag
        georef = Georeference(f"{GEOREF_PROTOCOL}ABC123#rgb")
        self.assertEqual(georef.item_id, "ABC123")
        self.assertEqual(georef.asset_tag, "rgb")

    def test_invalid_initialization(self):
        """Test initialization with invalid georeference strings"""
        # Test missing protocol
        with self.assertRaises(ValueError):
            Georeference("ABC123")

        # Test empty ID
        with self.assertRaises(ValueError):
            Georeference(f"{GEOREF_PROTOCOL}")

        # Test empty asset tag
        with self.assertRaises(ValueError):
            Georeference(f"{GEOREF_PROTOCOL}ABC123#")

    def test_new_random(self):
        """Test generation of random georeferences"""
        # Test without asset tag
        georef = Georeference.new_random()
        self.assertTrue(str(georef).startswith(GEOREF_PROTOCOL))

        # Test with asset tag
        georef = Georeference.new_random(asset_tag="rgb")
        self.assertTrue(str(georef).startswith(GEOREF_PROTOCOL))
        self.assertTrue(str(georef).endswith("#rgb"))

    def test_from_parts(self):
        """Test creating georeference from parts"""
        # Test without asset tag
        georef = Georeference.from_parts("ABC123")
        self.assertEqual(str(georef), f"{GEOREF_PROTOCOL}ABC123")

        # Test with asset tag
        georef = Georeference.from_parts("ABC123", "rgb")
        self.assertEqual(str(georef), f"{GEOREF_PROTOCOL}ABC123#rgb")

    def test_equality(self):
        """Test equality comparison"""
        georef1 = Georeference(f"{GEOREF_PROTOCOL}ABC123#rgb")
        georef2 = Georeference(f"{GEOREF_PROTOCOL}ABC123#rgb")
        georef3 = Georeference(f"{GEOREF_PROTOCOL}ABC123")

        # Test equal georeferences
        self.assertEqual(georef1, georef2)

        # Test unequal georeferences
        self.assertNotEqual(georef1, georef3)

        # Test comparison with non-Georeference object
        self.assertNotEqual(georef1, "not a georeference")

    def test_string_representation(self):
        """Test string representation"""
        georef_str = f"{GEOREF_PROTOCOL}ABC123#rgb"
        georef = Georeference(georef_str)
        self.assertEqual(str(georef), georef_str)

    def test_new_from_timestamp(self):
        """
        Test creating a georeference from a timestamp.

        :raises: AssertionError if the georeference is not created correctly
        """
        # Test without asset tag or prefix
        georef = Georeference.new_from_timestamp()
        self.assertTrue(str(georef).startswith(GEOREF_PROTOCOL))
        self.assertIsNone(georef.asset_tag)

        # Test with asset tag, no prefix
        georef = Georeference.new_from_timestamp(asset_tag="rgb")
        self.assertTrue(str(georef).startswith(GEOREF_PROTOCOL))
        self.assertEqual(georef.asset_tag, "rgb")
        self.assertTrue(str(georef).endswith("#rgb"))

        # Test with prefix, no asset tag
        georef = Georeference.new_from_timestamp(prefix="test")
        self.assertTrue(str(georef).startswith(GEOREF_PROTOCOL))
        self.assertTrue("test-" in georef.item_id)
        self.assertIsNone(georef.asset_tag)

        # Test with both prefix and asset tag
        georef = Georeference.new_from_timestamp(asset_tag="rgb", prefix="test")
        self.assertTrue(str(georef).startswith(GEOREF_PROTOCOL))
        self.assertTrue("test-" in georef.item_id)
        self.assertEqual(georef.asset_tag, "rgb")
        self.assertTrue(str(georef).endswith("#rgb"))

    def test_timestamp_ordering(self):
        """
        Test that timestamp-based georeferences increase over time.

        :raises: AssertionError if the ordering is incorrect
        """
        # Create first georeference
        georef1 = Georeference.new_from_timestamp()

        # Wait a small amount of time to ensure different timestamps
        time.sleep(0.01)

        # Create second georeference
        georef2 = Georeference.new_from_timestamp()

        # Convert back to timestamps for comparison
        # Extract the item_id (base36 string)
        id1 = georef1.item_id
        id2 = georef2.item_id

        # Convert base36 to integers
        timestamp1 = int(id1, 36)
        timestamp2 = int(id2, 36)

        # The second timestamp should be greater than the first
        self.assertGreater(timestamp2, timestamp1)

    def test_timestamp_ordering_with_prefix(self):
        """
        Test that timestamp-based georeferences with prefixes increase over time.

        :raises: AssertionError if the ordering is incorrect
        """
        # Create first georeference with prefix
        georef1 = Georeference.new_from_timestamp(prefix="test")

        # Wait a small amount of time to ensure different timestamps
        time.sleep(0.01)

        # Create second georeference with same prefix
        georef2 = Georeference.new_from_timestamp(prefix="test")

        # Extract the item_id (base36 string with prefix)
        id1 = georef1.item_id
        id2 = georef2.item_id

        # Verify both have the prefix
        self.assertTrue(id1.startswith("test-"))
        self.assertTrue(id2.startswith("test-"))

        # Extract the timestamp part (after the prefix)
        timestamp_str1 = id1.split("-", 1)[1]
        timestamp_str2 = id2.split("-", 1)[1]

        # Convert base36 to integers
        timestamp1 = int(timestamp_str1, 36)
        timestamp2 = int(timestamp_str2, 36)

        # The second timestamp should be greater than the first
        self.assertGreater(timestamp2, timestamp1)


if __name__ == "__main__":
    unittest.main()
