#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from pystac import Item

from aws.osml.geoagents.common import Georeference, LocalAssets, Workspace


class TestLocalAssets(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.workspace = Mock(spec=Workspace)
        self.georef = Mock(spec=Georeference)
        self.georef.asset_tag = "test_asset"
        self.test_item = Mock(spec=Item)
        self.test_assets = {"test_asset": Path("/tmp/test/data.geojson")}

        # Configure workspace mock behavior
        self.workspace.get_item.return_value = self.test_item
        self.workspace.download_assets.return_value = self.test_assets

    def test_successful_asset_management(self):
        """Test successful download and cleanup of assets."""
        # Create mock Path that "exists"
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.unlink = Mock()

        with patch.dict(self.test_assets, {"test_asset": mock_path}):
            # Use context manager
            with LocalAssets(self.georef, self.workspace) as (item, local_asset_paths):
                # Verify the download occurred correctly
                self.workspace.get_item.assert_called_once_with(self.georef)
                self.workspace.download_assets.assert_called_once_with(self.test_item, ["test_asset"])

                # Verify we got back the expected data
                self.assertEqual(item, self.test_item)
                self.assertEqual(local_asset_paths, self.test_assets)

                # Verify files haven't been deleted yet
                mock_path.unlink.assert_not_called()

            # Verify cleanup occurred after context exit
            mock_path.exists.assert_called()
            mock_path.unlink.assert_called_once()

    def test_cleanup_on_exception(self):
        """Test that assets are cleaned up even when an exception occurs."""
        # Create mock Path that "exists"
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.unlink = Mock()

        with patch.dict(self.test_assets, {"test_asset": mock_path}):
            try:
                with LocalAssets(self.georef, self.workspace):
                    raise Exception("Test exception")
            except Exception as e:
                self.assertEqual(str(e), "Test exception")

            # Verify cleanup occurred despite the exception
            mock_path.exists.assert_called()
            mock_path.unlink.assert_called_once()

    def test_no_asset_tag(self):
        """Test behavior when georeference has no asset tag."""
        self.georef.asset_tag = None

        with LocalAssets(self.georef, self.workspace) as (item, _):
            self.workspace.get_item.assert_called_once_with(self.georef)
            self.workspace.download_assets.assert_called_once_with(self.test_item, None)
            self.assertEqual(item, self.test_item)

    def test_nonexistent_asset_cleanup(self):
        """Test cleanup behavior with nonexistent assets."""
        # Create mock Path that doesn't "exist"
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = False
        mock_path.unlink = Mock()

        with patch.dict(self.test_assets, {"test_asset": mock_path}):
            with LocalAssets(self.georef, self.workspace):
                pass

            # Verify exists was checked but unlink wasn't called
            mock_path.exists.assert_called()
            mock_path.unlink.assert_not_called()

    def test_download_error_handling(self):
        """Test error handling when workspace operations fail."""
        self.workspace.get_item.side_effect = Exception("Download error")

        with self.assertRaises(ValueError) as context:
            with LocalAssets(self.georef, self.workspace):
                pass

        self.assertIn("Unable to access the dataset", str(context.exception))


if __name__ == "__main__":
    unittest.main()
