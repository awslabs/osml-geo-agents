#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

import boto3
from boto3.s3.transfer import TransferConfig
from pystac import Asset, Item

from aws.osml.geoagents.common.georeference import Georeference

logger = logging.getLogger(__name__)


class Workspace:
    """
    A workspace that manages STAC items and their local cached assets.

    This implementation works directly with S3 without benefit of a catalog or index. It is
    intended to provide a bare minimum level of functionality for the early stages of the
    geoagent development work. Eventually it will be replaced with an interface to a more
    full-featured workspace that allows search through integration with an actual STAC
    service.
    """

    def __init__(self, user_id: str, workspace_bucket: str, local_storage_path: Path | str):
        """
        Construct a new workspace that can be used to manage content stored in S3 and a
        ephemeral cache on a local disk volume.

        :param user_id: the id of the user or team that owns this logical workspace
        :param workspace_bucket: the name of the S3 bucket providing permanent storage for items
        :param local_storage_path: the local disk volume to cache items
        """
        self.user_id = user_id
        # TODO: Remove this "shared" override. It is only being used for testing until we can
        #       implement functions to properly load content to the workspace.
        logger.warning("DANGER: All workspace items are currently shared!")
        self.user_id = "shared"
        self.workspace_bucket = workspace_bucket
        self.session_local_path = Path(local_storage_path, self.user_id)
        self.session_local_path.mkdir(parents=True, exist_ok=True)

        self.s3_client = boto3.client("s3")
        self.s3_transfer_config = TransferConfig(
            multipart_threshold=8 * 1024 * 1024,
            max_concurrency=10,
            multipart_chunksize=8 * 1024 * 1024,
            use_threads=True,  # 8MB  # 8MB
        )

    def get_item(self, georef: Georeference) -> Item:
        """
        This method returns the STAC Item (summary information) for a georeference.
        It currently retrieves this item directly from S3 but eventually should likely
        look the item up in the index for the STAC.

        :param georef: the geo reference to retrieve
        :return: the STAC item
        """
        # Construct the S3 key for the item JSON
        item_key = f"{self.user_id}/{georef.item_id}/item.json"

        try:
            # Get the item JSON from S3
            response = self.s3_client.get_object(Bucket=self.workspace_bucket, Key=item_key)

            # Parse the JSON content and create a STAC item
            item_data = json.loads(response["Body"].read().decode("utf-8"))
            return Item.from_dict(item_data)
        except Exception as e:
            raise Exception(f"Failed to retrieve item from S3: {str(e)}") from e

    def download_assets(self, item: Item, selected_asset_keys: Optional[List[str]]) -> Dict[str, Path]:
        """
        Download assets from the item from the workspace storage and cache them on
        the local ephemeral disk.

        :param item: the STAC item with assets to download
        :param selected_asset_keys: an optional list of asset keys to download
        :return: a map between asset keys and their path on the local disk
        """
        if not item:
            raise ValueError("item can not be None.")

        asset_paths = {}

        # Filter assets if selected_asset_keys is provided
        assets_to_download = item.assets
        if selected_asset_keys:
            assets_to_download = {k: v for k, v in item.assets.items() if k in selected_asset_keys}

        for asset_key, asset in assets_to_download.items():
            # Parse the S3 URL for the asset, the assumption is that these are not generic
            # STAC items but instead just catalog entries for data stored in the S3 bucket
            # controlled by this workspace.
            parsed_url = urlparse(asset.href)
            if parsed_url.scheme != "s3":
                raise ValueError(f"Asset {asset_key} href is not an S3 URL: {asset.href}")
            bucket_name = parsed_url.netloc
            key = parsed_url.path.lstrip("/")

            # Ensure the local directory to store the assets exists and build a local file
            # path for the asset.
            asset_dir = self.session_local_path / asset_key
            asset_dir.mkdir(parents=True, exist_ok=True)
            local_path = Path(asset_dir, os.path.basename(key))

            # If the file hasn't already been downloaded pull it from S3 using the transfer
            # manager. The transfer manager uses multiple threads and takes advantage of
            # multipart downloads so this should be efficient for even large assets.
            if not local_path.exists():
                try:
                    self.s3_client.download_file(
                        Bucket=bucket_name,
                        Key=key,
                        Filename=str(local_path.absolute()),
                        Config=self.s3_transfer_config,
                        Callback=lambda bytes_transferred: logger.info(
                            f"Downloading {asset_key}: {bytes_transferred} bytes transferred"
                        ),
                    )
                    logger.info(f"Completed downloading {asset_key}")
                except Exception as e:
                    logger.warning(f"Error downloading {asset_key}: {str(e)}")
                    if local_path.exists():
                        local_path.unlink()  # Remove partially downloaded file
                    continue

            asset_paths[asset_key] = local_path

        return asset_paths

    def publish_item(self, item: Item, local_assets: Optional[Dict[str, Path]]) -> Georeference:
        """
        Publish an item/assets that only exist in the local ephemeral storage to the workspace.
        The item itself does not need to have an array of assets defined. Instead, an optional dictionary that
        maps asset keys to local paths will be used to create assets. Each local file will be transferred to the
        S3 storage bucket for the workspace and then the STAC Item asset hrefs will be updated to point to those
        S3 locations. After update the final STAC Item will also be persisted to S3 though this part should
        eventually be replaced with code to publish the Item to a STAC index.

        :param item: the STAC item to publish
        :param local_assets: a mapping of asset keys to local files
        :return: the georeference for the new item
        """
        if local_assets:
            for asset_key, local_path in local_assets.items():
                try:
                    # Construct S3 key for the asset and upload the asset to the
                    # workspace managed S3 bucket
                    asset_s3_key = f"{self.user_id}/{item.id}/{asset_key}/{local_path.name}"
                    self.s3_client.upload_file(
                        Filename=str(local_path.absolute()),
                        Bucket=self.workspace_bucket,
                        Key=asset_s3_key,
                        Config=self.s3_transfer_config,
                        Callback=lambda bytes_transferred: logger.info(
                            f"Uploading {asset_key}: {bytes_transferred} bytes transferred"
                        ),
                    )
                    logger.info(f"Completed uploading {asset_key}")

                    # Add a new asset to the STAC Item that has a href property
                    # correctly set to point to the location of the asset in the
                    # workspace managed S3 storage.
                    # TODO: Consider adding support for other properties on the STAC Asset.
                    #       The ability to set media type, title, description, etc. for
                    #       individual assets might eventually become useful. It may be
                    #       easiest to assume the item asset map already contains this
                    #       information and then we would only need to update the href
                    #       in this code.
                    s3_url = f"s3://{self.workspace_bucket}/{asset_s3_key}"
                    item.add_asset(asset_key, Asset(href=s3_url))

                except Exception as e:
                    logger.warning(f"Error uploading {asset_key}: {str(e)}")
                    raise Exception(f"Failed to upload asset {asset_key}: {str(e)}")

        # Construct S3 key for the item JSON
        item_s3_key = f"{self.user_id}/{item.id}/item.json"

        # Convert item to JSON
        item_json = json.dumps(item.to_dict())

        try:
            # Upload item JSON to S3
            self.s3_client.put_object(Bucket=self.workspace_bucket, Key=item_s3_key, Body=item_json)
        except Exception as e:
            logger.warning(f"\nError uploading {item_s3_key}: {str(e)}")
            raise Exception(f"Failed to upload item JSON: {str(e)}")

        # Create and return Georeference
        return Georeference.from_parts(item_id=item.id)
