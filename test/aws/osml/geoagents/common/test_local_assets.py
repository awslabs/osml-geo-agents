#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from unittest.mock import Mock, patch

from aws.osml.geoagents.common import GeoDataReference, LocalAssets, Workspace


class TestLocalAssets(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Set up mocks for Workspace
        self.workspace = Mock(spec=Workspace)
        self.workspace.prefix = "workspace/prefix"
        self.workspace.filesystem = Mock()

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

        # Create a STAC reference for testing
        self.stac_ref_str = "stac:test_item_id"
        self.stac_ref_with_asset_str = "stac:test_item_id#s3_asset"
        self.stac_ref_with_collections_str = "stac:collection1/collection2/test_item_id"
        self.stac_ref_with_collections_and_asset_str = "stac:collection1/collection2/test_item_id#s3_asset"

        # Create a WKT reference for testing
        self.wkt_ref_str = "POINT(0 0)"

        # Create a file path reference for testing
        self.file_path_ref_str = "/path/to/data.geojson"

    def test_resolve_reference_to_assets_stac(self):
        """Test processing of STAC reference."""
        # Create a GeoDataReference for STAC
        geo_data_ref = GeoDataReference(self.stac_ref_str)

        # Call the method under test
        item, asset_paths = LocalAssets.resolve_reference_to_assets(geo_data_ref, self.workspace)

        # Verify the item is returned correctly
        self.assertEqual(item, self.test_item)

        # Verify each asset href is processed correctly
        self.assertEqual(asset_paths["s3_asset"], "s3://bucket/path/to/file.tif")
        self.assertEqual(asset_paths["file_asset"], "file:///path/to/file.tif")
        self.assertEqual(
            asset_paths["relative_asset"], f"{self.workspace.prefix}/{self.test_item.id}/relative_asset/test.geojson"
        )

    def test_resolve_reference_to_assets_stac_with_collections(self):
        """Test processing of STAC reference with collections."""
        # Create a GeoDataReference for STAC with collections
        geo_data_ref = GeoDataReference(self.stac_ref_with_collections_str)

        # Call the method under test
        item, asset_paths = LocalAssets.resolve_reference_to_assets(geo_data_ref, self.workspace)

        # Verify the item is returned correctly
        self.assertEqual(item, self.test_item)

        # Verify each asset href is processed correctly with collections path
        self.assertEqual(asset_paths["s3_asset"], "s3://bucket/path/to/file.tif")
        self.assertEqual(asset_paths["file_asset"], "file:///path/to/file.tif")
        self.assertEqual(
            asset_paths["relative_asset"],
            f"{self.workspace.prefix}/collection1/collection2/{self.test_item.id}/relative_asset/test.geojson",
        )

    def test_resolve_reference_to_assets_stac_with_collections_and_asset_tag(self):
        """Test STAC reference with collections and a specific asset tag."""
        # Create a GeoDataReference for STAC with collections and asset tag
        geo_data_ref = GeoDataReference(self.stac_ref_with_collections_and_asset_str)

        # Call the method under test
        item, asset_paths = LocalAssets.resolve_reference_to_assets(geo_data_ref, self.workspace)

        # Verify only the specified asset is included
        self.assertEqual(len(asset_paths), 1)
        self.assertIn("s3_asset", asset_paths)
        self.assertEqual(asset_paths["s3_asset"], "s3://bucket/path/to/file.tif")

    def test_resolve_reference_to_assets_stac_with_asset_tag(self):
        """Test STAC reference with a specific asset tag."""
        # Create a GeoDataReference for STAC with asset tag
        geo_data_ref = GeoDataReference(self.stac_ref_with_asset_str)

        # Call the method under test
        item, asset_paths = LocalAssets.resolve_reference_to_assets(geo_data_ref, self.workspace)

        # Verify only the specified asset is included
        self.assertEqual(len(asset_paths), 1)
        self.assertIn("s3_asset", asset_paths)
        self.assertEqual(asset_paths["s3_asset"], "s3://bucket/path/to/file.tif")

    def test_resolve_reference_to_assets_stac_item_not_found(self):
        """Test when workspace.get_item returns None for STAC reference."""
        # Configure workspace to return None
        self.workspace.get_item.return_value = None

        # Create a GeoDataReference for STAC
        geo_data_ref = GeoDataReference(self.stac_ref_str)

        # Verify the method raises ValueError
        with self.assertRaises(ValueError):
            LocalAssets.resolve_reference_to_assets(geo_data_ref, self.workspace)

    def test_resolve_reference_to_assets_stac_workspace_exception(self):
        """Test when workspace.get_item raises an exception for STAC reference."""
        # Configure workspace to raise an exception
        self.workspace.get_item.side_effect = Exception("Workspace error")

        # Create a GeoDataReference for STAC
        geo_data_ref = GeoDataReference(self.stac_ref_str)

        # Verify the method raises ValueError
        with self.assertRaises(ValueError):
            LocalAssets.resolve_reference_to_assets(geo_data_ref, self.workspace)

    @patch("tempfile.NamedTemporaryFile")
    def test_resolve_reference_to_assets_wkt(self, mock_temp_file):
        """Test processing of WKT reference."""
        # Mock the temporary file
        mock_temp = Mock()
        mock_temp.name = "/tmp/temp_wkt_file.wkt"
        mock_temp_file.return_value = mock_temp

        # Create a GeoDataReference for WKT
        geo_data_ref = GeoDataReference(self.wkt_ref_str)

        # Call the method under test
        item, asset_paths = LocalAssets.resolve_reference_to_assets(geo_data_ref, self.workspace)

        # Verify the item is None for WKT reference
        self.assertIsNone(item)

        # Verify the asset path is set correctly
        self.assertEqual(len(asset_paths), 1)
        self.assertIn("wkt", asset_paths)
        self.assertEqual(asset_paths["wkt"], mock_temp.name)

    @patch.object(LocalAssets, "_resolve_file_path")
    def test_resolve_reference_to_assets_file_path(self, mock_resolve_file_path):
        """Test processing of file path reference."""
        # Create a GeoDataReference for file path
        geo_data_ref = GeoDataReference(self.file_path_ref_str)

        # Configure the mock to return a resolved path
        resolved_path = "/resolved/path/to/data.geojson"
        mock_resolve_file_path.return_value = resolved_path

        # Call the method under test
        item, asset_paths = LocalAssets.resolve_reference_to_assets(geo_data_ref, self.workspace)

        # Verify the item is None for file path reference
        self.assertIsNone(item)

        # Verify _resolve_file_path was called with the correct arguments
        mock_resolve_file_path.assert_called_once_with(self.file_path_ref_str, self.workspace)

        # Verify the asset path is set correctly with the resolved path
        self.assertEqual(len(asset_paths), 1)
        self.assertIn("data.geojson", asset_paths)
        self.assertEqual(asset_paths["data.geojson"], resolved_path)

    def test_context_manager_stac(self):
        """Test the LocalAssets context manager with STAC reference."""
        # Create a GeoDataReference for STAC
        geo_data_ref = GeoDataReference(self.stac_ref_str)

        # Create a LocalAssets instance
        local_assets = LocalAssets(geo_data_ref, self.workspace)

        # Use it as a context manager
        with local_assets as (item, asset_paths):
            # Verify the returned values
            self.assertEqual(item, self.test_item)
            self.assertEqual(asset_paths["s3_asset"], "s3://bucket/path/to/file.tif")
            self.assertEqual(asset_paths["file_asset"], "file:///path/to/file.tif")
            self.assertEqual(
                asset_paths["relative_asset"], f"{self.workspace.prefix}/{self.test_item.id}/relative_asset/test.geojson"
            )

    def test_context_manager_stac_with_collections(self):
        """Test the LocalAssets context manager with STAC reference including collections."""
        # Create a GeoDataReference for STAC with collections
        geo_data_ref = GeoDataReference(self.stac_ref_with_collections_str)

        # Create a LocalAssets instance
        local_assets = LocalAssets(geo_data_ref, self.workspace)

        # Use it as a context manager
        with local_assets as (item, asset_paths):
            # Verify the returned values
            self.assertEqual(item, self.test_item)
            self.assertEqual(asset_paths["s3_asset"], "s3://bucket/path/to/file.tif")
            self.assertEqual(asset_paths["file_asset"], "file:///path/to/file.tif")
            self.assertEqual(
                asset_paths["relative_asset"],
                f"{self.workspace.prefix}/collection1/collection2/{self.test_item.id}/relative_asset/test.geojson",
            )

    @patch("tempfile.NamedTemporaryFile")
    def test_context_manager_wkt(self, mock_temp_file):
        """Test the LocalAssets context manager with WKT reference."""
        # Mock the temporary file
        mock_temp = Mock()
        mock_temp.name = "/tmp/temp_wkt_file.wkt"
        mock_temp_file.return_value = mock_temp

        # Create a GeoDataReference for WKT
        geo_data_ref = GeoDataReference(self.wkt_ref_str)

        # Create a LocalAssets instance
        local_assets = LocalAssets(geo_data_ref, self.workspace)

        # Use it as a context manager
        with local_assets as (item, asset_paths):
            # Verify the returned values
            self.assertIsNone(item)
            self.assertEqual(len(asset_paths), 1)
            self.assertIn("wkt", asset_paths)
            self.assertEqual(asset_paths["wkt"], mock_temp.name)

    @patch.object(LocalAssets, "_resolve_file_path")
    def test_context_manager_file_path(self, mock_resolve_file_path):
        """Test the LocalAssets context manager with file path reference."""
        # Create a GeoDataReference for file path
        geo_data_ref = GeoDataReference(self.file_path_ref_str)

        # Configure the mock to return a resolved path
        resolved_path = "/resolved/path/to/data.geojson"
        mock_resolve_file_path.return_value = resolved_path

        # Create a LocalAssets instance
        local_assets = LocalAssets(geo_data_ref, self.workspace)

        # Use it as a context manager
        with local_assets as (item, asset_paths):
            # Verify the returned values
            self.assertIsNone(item)

            # Verify _resolve_file_path was called with the correct arguments
            mock_resolve_file_path.assert_called_once_with(self.file_path_ref_str, self.workspace)

            # Verify the asset path is set correctly with the resolved path
            self.assertEqual(len(asset_paths), 1)
            self.assertIn("data.geojson", asset_paths)
            self.assertEqual(asset_paths["data.geojson"], resolved_path)

    def test_resolve_file_path_s3_url(self):
        """Test resolving an S3 URL file path."""
        # S3 URLs should be used directly
        s3_url = "s3://bucket/path/to/file.tif"
        result = LocalAssets._resolve_file_path(s3_url, self.workspace)
        self.assertEqual(result, s3_url)

    def test_resolve_file_path_absolute_path(self):
        """Test resolving an absolute file path."""
        # Absolute paths should be used directly
        abs_path = "/absolute/path/to/file.tif"
        result = LocalAssets._resolve_file_path(abs_path, self.workspace)
        self.assertEqual(result, abs_path)

    def test_resolve_file_path_relative_path_exists(self):
        """Test resolving a relative file path that exists."""
        # Relative paths with directory components should be combined with workspace prefix
        rel_path = "subdir/file.tif"
        full_path = f"{self.workspace.prefix}/{rel_path}"

        # Configure filesystem mock to indicate the file exists
        self.workspace.filesystem.exists.return_value = True

        result = LocalAssets._resolve_file_path(rel_path, self.workspace)
        self.assertEqual(result, full_path)
        self.workspace.filesystem.exists.assert_called_once_with(full_path)

    def test_resolve_file_path_relative_path_not_exists(self):
        """Test resolving a relative file path that doesn't exist."""
        # Relative paths with directory components should be combined with workspace prefix
        rel_path = "subdir/file.tif"
        full_path = f"{self.workspace.prefix}/{rel_path}"

        # Configure filesystem mock to indicate the file doesn't exist
        self.workspace.filesystem.exists.return_value = False

        with self.assertRaises(ValueError) as context:
            LocalAssets._resolve_file_path(rel_path, self.workspace)

        self.assertIn(f"File not found at path: {full_path}", str(context.exception))
        self.workspace.filesystem.exists.assert_called_once_with(full_path)

    def test_resolve_file_path_filename_single_match(self):
        """Test resolving a filename with a single match."""
        # Just a filename should be searched for in the workspace
        filename = "file.tif"
        matching_path = f"{self.workspace.prefix}/subdir/file.tif"

        # Configure filesystem mock to return a single matching file
        self.workspace.filesystem.find.return_value = [matching_path]

        result = LocalAssets._resolve_file_path(filename, self.workspace)
        self.assertEqual(result, matching_path)
        self.workspace.filesystem.find.assert_called_once_with(self.workspace.prefix, maxdepth=None)

    def test_resolve_file_path_filename_multiple_matches(self):
        """Test resolving a filename with multiple matches."""
        # Just a filename should be searched for in the workspace
        filename = "file.tif"
        matching_paths = [f"{self.workspace.prefix}/subdir1/file.tif", f"{self.workspace.prefix}/subdir2/file.tif"]

        # Configure filesystem mock to return multiple matching files
        self.workspace.filesystem.find.return_value = matching_paths

        with self.assertRaises(ValueError) as context:
            LocalAssets._resolve_file_path(filename, self.workspace)

        self.assertIn(f"Multiple files with name '{filename}' found in workspace", str(context.exception))
        self.workspace.filesystem.find.assert_called_once_with(self.workspace.prefix, maxdepth=None)

    def test_resolve_file_path_filename_no_match(self):
        """Test resolving a filename with no matches."""
        # Just a filename should be searched for in the workspace
        filename = "file.tif"

        # Configure filesystem mock to return no matching files
        self.workspace.filesystem.find.return_value = []

        with self.assertRaises(ValueError) as context:
            LocalAssets._resolve_file_path(filename, self.workspace)

        self.assertIn(f"No file with name '{filename}' found in workspace", str(context.exception))
        self.workspace.filesystem.find.assert_called_once_with(self.workspace.prefix, maxdepth=None)


if __name__ == "__main__":
    unittest.main()
