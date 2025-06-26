#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from unittest.mock import Mock

from aws.osml.geoagents.common import Georeference, LocalAssets, Workspace


class TestLocalAssets(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Set up mocks for Workspace and Georeference
        self.workspace = Mock(spec=Workspace)
        self.workspace.prefix = "workspace/prefix"
        self.georef = Mock(spec=Georeference)
        self.georef.asset_tag = None  # Initially no asset tag filter

        # Create a mock STAC Item with three different asset types
        self.test_item = Mock()
        self.test_item.id = "test_item_id"

        # Create assets with different href types
        s3_asset = Mock()
        s3_asset.href = "s3://bucket/path/to/file.tif"

        file_asset = Mock()
        file_asset.href = "file:///path/to/file.tif"

        relative_asset = Mock()
        relative_asset.href = "foo/bar/test.geojson"

        # Add assets to the item
        self.test_item.assets = {"s3_asset": s3_asset, "file_asset": file_asset, "relative_asset": relative_asset}

        # Configure workspace mock to return our test item
        self.workspace.get_item.return_value = self.test_item

    def test_resolve_reference_to_assets_all_types(self):
        """Test processing of all three href types in one go."""
        # Call the method under test
        item, asset_paths = LocalAssets.resolve_reference_to_assets(self.georef, self.workspace)

        # Verify the item is returned correctly
        self.assertEqual(item, self.test_item)

        # Verify each asset href is processed correctly
        self.assertEqual(asset_paths["s3_asset"], "s3://bucket/path/to/file.tif")
        self.assertEqual(asset_paths["file_asset"], "file:///path/to/file.tif")
        self.assertEqual(
            asset_paths["relative_asset"], f"{self.workspace.prefix}/{self.test_item.id}/relative_asset/test.geojson"
        )

    def test_resolve_reference_to_assets_with_asset_tag(self):
        """Test with a specific asset tag."""
        # Set a specific asset tag
        self.georef.asset_tag = "s3_asset"

        # Call the method under test
        item, asset_paths = LocalAssets.resolve_reference_to_assets(self.georef, self.workspace)

        # Verify only the specified asset is included
        self.assertEqual(len(asset_paths), 1)
        self.assertIn("s3_asset", asset_paths)
        self.assertEqual(asset_paths["s3_asset"], "s3://bucket/path/to/file.tif")

    def test_resolve_reference_to_assets_item_not_found(self):
        """Test when workspace.get_item returns None."""
        # Configure workspace to return None
        self.workspace.get_item.return_value = None

        # Verify the method raises ValueError
        with self.assertRaises(ValueError):
            LocalAssets.resolve_reference_to_assets(self.georef, self.workspace)

    def test_resolve_reference_to_assets_workspace_exception(self):
        """Test when workspace.get_item raises an exception."""
        # Configure workspace to raise an exception
        self.workspace.get_item.side_effect = Exception("Workspace error")

        # Verify the method raises ValueError
        with self.assertRaises(ValueError):
            LocalAssets.resolve_reference_to_assets(self.georef, self.workspace)

    def test_context_manager(self):
        """Test the LocalAssets context manager."""
        # Create a LocalAssets instance
        local_assets = LocalAssets(self.georef, self.workspace)

        # Use it as a context manager
        with local_assets as (item, asset_paths):
            # Verify the returned values
            self.assertEqual(item, self.test_item)
            self.assertEqual(asset_paths["s3_asset"], "s3://bucket/path/to/file.tif")
            self.assertEqual(asset_paths["file_asset"], "file:///path/to/file.tif")
            self.assertEqual(
                asset_paths["relative_asset"], f"{self.workspace.prefix}/{self.test_item.id}/relative_asset/test.geojson"
            )


if __name__ == "__main__":
    unittest.main()
