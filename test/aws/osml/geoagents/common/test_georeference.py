#  Copyright 2025 Amazon.com, Inc. or its affiliates.

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


if __name__ == "__main__":
    unittest.main()
