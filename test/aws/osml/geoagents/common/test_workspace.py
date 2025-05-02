#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import json
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import boto3
from moto import mock_aws
from pystac import Asset, Item

from aws.osml.geoagents.common import Georeference, Workspace


class TestWorkspace(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test method"""

        self.mock_aws = mock_aws()
        self.mock_aws.start()

        self.s3 = boto3.client("s3")
        self.bucket_name = "XXXXXXXXXXXXXXXXXXXXX"
        self.user_id = "shared"

        # Create the test bucket
        self.s3.create_bucket(Bucket=self.bucket_name)

        # Create temporary directory
        self.tmp_path = tempfile.mkdtemp()

        # Initialize workspace
        self.workspace = Workspace(user_id=self.user_id, workspace_bucket=self.bucket_name, local_storage_path=self.tmp_path)

    def tearDown(self):
        """Clean up after each test method"""
        # Clean up local files
        shutil.rmtree(self.tmp_path)

        self.mock_aws.stop()

    def create_sample_stac_item(self):
        """Helper method to create a sample STAC item"""
        return Item(
            id="012345",
            geometry={"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
            bbox=[0, 0, 1, 1],
            datetime=datetime.fromisoformat("2025-04-23T14:05:23Z"),
            properties={},
        )

    def test_get_item(self):
        """Test getting an item from S3"""
        # Create a sample STAC item
        sample_item = self.create_sample_stac_item()

        # Add a test asset
        sample_item.add_asset(
            "test-asset",
            Asset(href=f"s3://{self.bucket_name}/{self.user_id}/{sample_item.id}/test-asset.txt", media_type="text/plain"),
        )

        # Upload the item to S3
        item_key = f"{self.user_id}/{sample_item.id}/item.json"
        self.s3.put_object(Bucket=self.bucket_name, Key=item_key, Body=json.dumps(sample_item.to_dict()))

        # Test get_item
        georef = Georeference.from_parts(item_id=sample_item.id)
        retrieved_item = self.workspace.get_item(georef)

        assert retrieved_item.id == sample_item.id
        assert "test-asset" in retrieved_item.assets

    def test_get_item_not_found(self):
        """Test getting a non-existent item"""
        georef = Georeference.from_parts(item_id="GEOREF-DOES-NOT-EXIST")

        with self.assertRaises(Exception) as exc_info:
            self.workspace.get_item(georef)
            assert "Failed to retrieve item from S3" in str(exc_info)

    def test_download_assets(self):
        """Test downloading assets from S3"""
        # Create a sample STAC item with asset
        sample_item = self.create_sample_stac_item()
        asset_key = f"{self.user_id}/{sample_item.id}/test-asset/test-asset.txt"
        sample_item.add_asset("test-asset", Asset(href=f"s3://{self.bucket_name}/{asset_key}", media_type="text/plain"))

        # Upload test asset to mock S3
        test_content = b"test file content"
        self.s3.put_object(Bucket=self.bucket_name, Key=asset_key, Body=test_content)

        # Test download_assets
        asset_paths = self.workspace.download_assets(sample_item, ["test-asset"])

        assert "test-asset" in asset_paths
        assert asset_paths["test-asset"].exists()
        assert asset_paths["test-asset"].read_bytes() == test_content

    def test_publish_item(self):
        """Test publishing an item to S3"""
        # Create test item and asset
        sample_item = self.create_sample_stac_item()
        test_asset_path = Path(self.tmp_path, "test-asset.txt")
        test_content = b"test file content"
        with open(test_asset_path, "wb") as out:
            out.write(test_content)

        local_assets = {"test-asset": test_asset_path}

        # Test publish_item
        georef = self.workspace.publish_item(sample_item, local_assets)
        assert georef is not None

        # Verify asset upload
        s3_key = f"{self.user_id}/{sample_item.id}/test-asset/{test_asset_path.name}"
        response = self.s3.get_object(Bucket=self.bucket_name, Key=s3_key)
        assert response["Body"].read() == test_content

        # Verify item JSON upload
        item_key = f"{self.user_id}/{sample_item.id}/item.json"
        response = self.s3.get_object(Bucket=self.bucket_name, Key=item_key)
        uploaded_item = Item.from_dict(json.loads(response["Body"].read().decode("utf-8")))
        assert uploaded_item.id == sample_item.id
        assert uploaded_item.assets["test-asset"].href.startswith(f"s3://{self.bucket_name}")

    def test_publish_item_no_assets(self):
        """Test publishing an item without assets"""
        sample_item = self.create_sample_stac_item()

        # Test publish_item without assets
        georef = self.workspace.publish_item(sample_item, None)
        assert georef is not None

        # Verify item JSON upload
        item_key = f"{self.user_id}/{sample_item.id}/item.json"
        response = self.s3.get_object(Bucket=self.bucket_name, Key=item_key)
        uploaded_item = Item.from_dict(json.loads(response["Body"].read().decode("utf-8")))
        assert uploaded_item.id == sample_item.id
