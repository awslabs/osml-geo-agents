#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import time
import unittest

from aws.osml.geoagents.common import STAC_PROTOCOL, STACReference


class TestSTACReference(unittest.TestCase):
    def test_valid_initialization(self):
        """Test initialization with valid STAC reference strings"""
        # Test without asset tag
        stac_ref = STACReference(f"{STAC_PROTOCOL}ABC123")
        self.assertEqual(stac_ref.item_id, "ABC123")
        self.assertIsNone(stac_ref.asset_tag)
        self.assertEqual(stac_ref.collections, [])

        # Test with asset tag
        stac_ref = STACReference(f"{STAC_PROTOCOL}ABC123#rgb")
        self.assertEqual(stac_ref.item_id, "ABC123")
        self.assertEqual(stac_ref.asset_tag, "rgb")
        self.assertEqual(stac_ref.collections, [])

        # Test with single collection
        stac_ref = STACReference(f"{STAC_PROTOCOL}foo/ABC123")
        self.assertEqual(stac_ref.item_id, "ABC123")
        self.assertIsNone(stac_ref.asset_tag)
        self.assertEqual(stac_ref.collections, ["foo"])

        # Test with multiple collections
        stac_ref = STACReference(f"{STAC_PROTOCOL}foo/bar/ABC123")
        self.assertEqual(stac_ref.item_id, "ABC123")
        self.assertIsNone(stac_ref.asset_tag)
        self.assertEqual(stac_ref.collections, ["foo", "bar"])

        # Test with collections and asset tag
        stac_ref = STACReference(f"{STAC_PROTOCOL}foo/bar/ABC123#rgb")
        self.assertEqual(stac_ref.item_id, "ABC123")
        self.assertEqual(stac_ref.asset_tag, "rgb")
        self.assertEqual(stac_ref.collections, ["foo", "bar"])

    def test_invalid_initialization(self):
        """Test initialization with invalid STAC reference strings"""
        # Test missing protocol
        with self.assertRaises(ValueError):
            STACReference("ABC123")

        # Test empty ID
        with self.assertRaises(ValueError):
            STACReference(f"{STAC_PROTOCOL}")

        # Test empty asset tag
        with self.assertRaises(ValueError):
            STACReference(f"{STAC_PROTOCOL}ABC123#")

    def test_new_random(self):
        """Test generation of random STAC references"""
        # Test without asset tag
        stac_ref = STACReference.new_random()
        self.assertTrue(str(stac_ref).startswith(STAC_PROTOCOL))
        self.assertEqual(stac_ref.collections, [])

        # Test with asset tag
        stac_ref = STACReference.new_random(asset_tag="rgb")
        self.assertTrue(str(stac_ref).startswith(STAC_PROTOCOL))
        self.assertTrue(str(stac_ref).endswith("#rgb"))
        self.assertEqual(stac_ref.collections, [])

        # Test with single collection
        stac_ref = STACReference.new_random(collections=["foo"])
        self.assertTrue(str(stac_ref).startswith(f"{STAC_PROTOCOL}foo/"))
        self.assertEqual(stac_ref.collections, ["foo"])

        # Test with multiple collections
        stac_ref = STACReference.new_random(collections=["foo", "bar"])
        self.assertTrue(str(stac_ref).startswith(f"{STAC_PROTOCOL}foo/bar/"))
        self.assertEqual(stac_ref.collections, ["foo", "bar"])

        # Test with collections and asset tag
        stac_ref = STACReference.new_random(asset_tag="rgb", collections=["foo", "bar"])
        self.assertTrue(str(stac_ref).startswith(f"{STAC_PROTOCOL}foo/bar/"))
        self.assertTrue(str(stac_ref).endswith("#rgb"))
        self.assertEqual(stac_ref.collections, ["foo", "bar"])

    def test_from_parts(self):
        """Test creating STAC reference from parts"""
        # Test without asset tag
        stac_ref = STACReference.from_parts("ABC123")
        self.assertEqual(str(stac_ref), f"{STAC_PROTOCOL}ABC123")
        self.assertEqual(stac_ref.collections, [])

        # Test with asset tag
        stac_ref = STACReference.from_parts("ABC123", "rgb")
        self.assertEqual(str(stac_ref), f"{STAC_PROTOCOL}ABC123#rgb")
        self.assertEqual(stac_ref.collections, [])

        # Test with single collection
        stac_ref = STACReference.from_parts("ABC123", collections=["foo"])
        self.assertEqual(str(stac_ref), f"{STAC_PROTOCOL}foo/ABC123")
        self.assertEqual(stac_ref.collections, ["foo"])

        # Test with multiple collections
        stac_ref = STACReference.from_parts("ABC123", collections=["foo", "bar"])
        self.assertEqual(str(stac_ref), f"{STAC_PROTOCOL}foo/bar/ABC123")
        self.assertEqual(stac_ref.collections, ["foo", "bar"])

        # Test with collections and asset tag
        stac_ref = STACReference.from_parts("ABC123", "rgb", ["foo", "bar"])
        self.assertEqual(str(stac_ref), f"{STAC_PROTOCOL}foo/bar/ABC123#rgb")
        self.assertEqual(stac_ref.collections, ["foo", "bar"])

    def test_equality(self):
        """Test equality comparison"""
        stac_ref1 = STACReference(f"{STAC_PROTOCOL}ABC123#rgb")
        stac_ref2 = STACReference(f"{STAC_PROTOCOL}ABC123#rgb")
        stac_ref3 = STACReference(f"{STAC_PROTOCOL}ABC123")

        # Test equal STAC references
        self.assertEqual(stac_ref1, stac_ref2)

        # Test unequal STAC references
        self.assertNotEqual(stac_ref1, stac_ref3)

        # Test comparison with non-STACReference object
        self.assertNotEqual(stac_ref1, "not a STAC reference")

    def test_string_representation(self):
        """Test string representation"""
        stac_ref_str = f"{STAC_PROTOCOL}ABC123#rgb"
        stac_ref = STACReference(stac_ref_str)
        self.assertEqual(str(stac_ref), stac_ref_str)

    def test_new_from_timestamp(self):
        """
        Test creating a STAC reference from a timestamp.

        :raises: AssertionError if the STAC reference is not created correctly
        """
        # Test without asset tag or prefix
        stac_ref = STACReference.new_from_timestamp()
        self.assertTrue(str(stac_ref).startswith(STAC_PROTOCOL))
        self.assertIsNone(stac_ref.asset_tag)
        self.assertEqual(stac_ref.collections, [])

        # Test with asset tag, no prefix
        stac_ref = STACReference.new_from_timestamp(asset_tag="rgb")
        self.assertTrue(str(stac_ref).startswith(STAC_PROTOCOL))
        self.assertEqual(stac_ref.asset_tag, "rgb")
        self.assertTrue(str(stac_ref).endswith("#rgb"))
        self.assertEqual(stac_ref.collections, [])

        # Test with prefix, no asset tag
        stac_ref = STACReference.new_from_timestamp(prefix="test")
        self.assertTrue(str(stac_ref).startswith(STAC_PROTOCOL))
        self.assertTrue("test-" in stac_ref.item_id)
        self.assertIsNone(stac_ref.asset_tag)
        self.assertEqual(stac_ref.collections, [])

        # Test with both prefix and asset tag
        stac_ref = STACReference.new_from_timestamp(asset_tag="rgb", prefix="test")
        self.assertTrue(str(stac_ref).startswith(STAC_PROTOCOL))
        self.assertTrue("test-" in stac_ref.item_id)
        self.assertEqual(stac_ref.asset_tag, "rgb")
        self.assertTrue(str(stac_ref).endswith("#rgb"))
        self.assertEqual(stac_ref.collections, [])

        # Test with collections
        stac_ref = STACReference.new_from_timestamp(collections=["foo", "bar"])
        self.assertTrue(str(stac_ref).startswith(f"{STAC_PROTOCOL}foo/bar/"))
        self.assertEqual(stac_ref.collections, ["foo", "bar"])

        # Test with collections, prefix and asset tag
        stac_ref = STACReference.new_from_timestamp(asset_tag="rgb", prefix="test", collections=["foo", "bar"])
        self.assertTrue(str(stac_ref).startswith(f"{STAC_PROTOCOL}foo/bar/"))
        self.assertTrue("test-" in stac_ref.item_id)
        self.assertEqual(stac_ref.asset_tag, "rgb")
        self.assertTrue(str(stac_ref).endswith("#rgb"))
        self.assertEqual(stac_ref.collections, ["foo", "bar"])

    def test_timestamp_ordering(self):
        """
        Test that timestamp-based STAC references increase over time.

        :raises: AssertionError if the ordering is incorrect
        """
        # Create first STAC reference
        stac_ref1 = STACReference.new_from_timestamp()

        # Wait a small amount of time to ensure different timestamps
        time.sleep(0.01)

        # Create second STAC reference
        stac_ref2 = STACReference.new_from_timestamp()

        # Convert back to timestamps for comparison
        # Extract the item_id (base36 string)
        id1 = stac_ref1.item_id
        id2 = stac_ref2.item_id

        # Convert base36 to integers
        timestamp1 = int(id1, 36)
        timestamp2 = int(id2, 36)

        # The second timestamp should be greater than the first
        self.assertGreater(timestamp2, timestamp1)

    def test_timestamp_ordering_with_prefix(self):
        """
        Test that timestamp-based STAC references with prefixes increase over time.

        :raises: AssertionError if the ordering is incorrect
        """
        # Create first STAC reference with prefix
        stac_ref1 = STACReference.new_from_timestamp(prefix="test")

        # Wait a small amount of time to ensure different timestamps
        time.sleep(0.01)

        # Create second STAC reference with same prefix
        stac_ref2 = STACReference.new_from_timestamp(prefix="test")

        # Extract the item_id (base36 string with prefix)
        id1 = stac_ref1.item_id
        id2 = stac_ref2.item_id

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
