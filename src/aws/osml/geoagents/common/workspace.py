#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Set

import geopandas as gpd
import pyarrow.parquet as pq
from pystac import Asset, Item

from aws.osml.geoagents.common.georeference import Georeference

logger = logging.getLogger(__name__)


class Workspace:
    """
    A workspace that manages STAC items and their assets.

    This implementation works with any fsspec-compatible filesystem, including local file systems
    and S3. It provides a bare minimum level of functionality for the early stages of the
    geoagent development work. Eventually it will be replaced with an interface to a more
    full-featured workspace that allows search through integration with an actual STAC service.
    """

    def __init__(self, filesystem, prefix: str):
        """
        Construct a new workspace that can be used to manage content stored in any filesystem.

        :param filesystem: A fsspec filesystem object (S3FileSystem, LocalFileSystem, etc.)
        :param prefix: Path prefix identifying the workspace location in relation to the filesystem root
        """
        self.filesystem = filesystem
        self.prefix = prefix.rstrip("/")

        # For backward compatibility, extract user_id from prefix if it's the last component
        self.user_id = os.path.basename(self.prefix) if self.prefix else "shared"

    def get_item(self, georef: Georeference) -> Item:
        """
        This method returns the STAC Item (summary information) for a georeference.
        It retrieves this item directly from the filesystem but eventually should likely
        look the item up in the index for the STAC.

        :param georef: the geo reference to retrieve
        :return: the STAC item
        """
        # Construct the path for the item JSON
        item_path = f"{self.prefix}/{georef.item_id}/item.json"

        try:
            # Get the item JSON from the filesystem
            with self.filesystem.open(item_path, "rb") as f:
                item_data = json.loads(f.read().decode("utf-8"))
                return Item.from_dict(item_data)
        except Exception as e:
            raise Exception(f"Failed to retrieve item from filesystem: {str(e)}") from e

    def list_items(self) -> List[Georeference]:
        """
        List all items in the workspace.

        :return: a list of Georeference objects for each item
        """
        try:
            # Use filesystem's ls method to list directories
            item_ids: Set[str] = set()

            # List all directories at the prefix level
            try:
                # Get all directories at the prefix level
                dirs = self.filesystem.ls(self.prefix, detail=True)

                # Filter for directories only
                dirs = [d for d in dirs if d.get("type", None) == "directory"]

                for directory in dirs:
                    # Extract the item ID from the path
                    dir_path = directory["name"]
                    item_id = os.path.basename(dir_path.rstrip("/"))

                    # Verify this is an item by checking for item.json
                    item_json_path = f"{dir_path}/item.json"
                    if self.filesystem.exists(item_json_path):
                        item_ids.add(item_id)
            except FileNotFoundError:
                # If the prefix doesn't exist yet, return an empty list
                pass

            # Create Georeference objects for each item ID
            return [Georeference.from_parts(item_id=item_id) for item_id in item_ids]
        except Exception as e:
            logger.warning(f"Error listing items: {str(e)}")
            raise Exception(f"Failed to list items: {str(e)}")

    def delete_item(self, georef: Georeference) -> None:
        """
        Delete an item and all its assets from the workspace.

        :param georef: the georeference of the item to delete
        :raises Exception: if the item cannot be deleted
        """
        # Delete the item and its assets from the filesystem
        item_path = f"{self.prefix}/{georef.item_id}"

        try:
            # Check if the item exists
            if self.filesystem.exists(item_path):
                # Use recursive delete to remove the item directory and all contents
                self.filesystem.rm(item_path, recursive=True)
                logger.info(f"Deleted item {georef}")
            else:
                logger.warning(f"No objects found for item {georef}")
        except Exception as e:
            logger.warning(f"Error deleting item {georef}: {str(e)}")
            raise Exception(f"Failed to delete item {georef}: {str(e)}")

    def create_item(self, item: Item, temp_assets: Optional[Dict[str, Path]]) -> Georeference:
        """
        Create an item/assets in the workspace.

        The item itself does not need to have an array of assets defined. Instead, an optional dictionary that
        maps asset keys to temporary paths will be used to create assets. Each temporary file will be transferred to the
        filesystem for the workspace and then the STAC Item asset hrefs will be updated to point to those
        locations.

        :param item: the STAC item to create
        :param temp_assets: a mapping of asset keys to local files
        :return: the georeference for the new item
        """
        # Determine the base path for this item
        item_base_path = f"{self.prefix}/{item.id}"

        if temp_assets:
            for asset_key, local_path in temp_assets.items():
                try:
                    # Construct path for the asset in the filesystem
                    asset_path = f"{item_base_path}/{asset_key}/{local_path.name}"

                    # Make sure the directory exists
                    self.filesystem.makedirs(os.path.dirname(asset_path), exist_ok=True)

                    # Upload/copy the asset to the filesystem
                    with open(local_path, "rb") as src:
                        with self.filesystem.open(asset_path, "wb") as dst:
                            dst.write(src.read())

                    logger.info(f"Completed uploading {asset_key}")

                    # Add a new asset to the STAC Item that has a href property
                    # correctly set to point to the location of the asset in the filesystem
                    # For S3 filesystem, use s3:// URL format
                    if hasattr(self.filesystem, "protocol") and self.filesystem.protocol == "s3":
                        # Extract bucket name from the filesystem if available
                        bucket = getattr(self.filesystem, "bucket_name", None)
                        if bucket:
                            asset_url = f"s3://{bucket}/{asset_path}"
                        else:
                            # Fall back to relative path if bucket can't be determined
                            asset_url = asset_path
                    else:
                        # For local filesystem, use relative path
                        asset_url = asset_path

                    item.add_asset(asset_key, Asset(href=asset_url))

                except Exception as e:
                    logger.warning(f"Error uploading {asset_key}: {str(e)}")
                    raise Exception(f"Failed to upload asset {asset_key}: {str(e)}")

        # Construct path for the item JSON
        item_json_path = f"{item_base_path}/item.json"

        # Convert item to JSON
        item_json = json.dumps(item.to_dict())

        try:
            # Make sure the directory exists
            self.filesystem.makedirs(os.path.dirname(item_json_path), exist_ok=True)

            # Upload item JSON to the filesystem
            with self.filesystem.open(item_json_path, "w") as f:
                f.write(item_json)
        except Exception as e:
            logger.warning(f"\nError uploading {item_json_path}: {str(e)}")
            raise Exception(f"Failed to upload item JSON: {str(e)}")

        # Create and return Georeference
        return Georeference.from_parts(item_id=item.id)

    def is_parquet_file(self, file_path: str) -> bool:
        """
        Check if a file is a Parquet file by reading the magic bytes at the beginning of the file.

        :param file_path: Path to the file in the filesystem
        :return: True if the file is a Parquet file, False otherwise
        """
        # Parquet files start with PAR1 magic bytes
        try:
            with self.filesystem.open(file_path, "rb") as f:
                magic_bytes = f.read(4)
                return magic_bytes == b"PAR1"
        except Exception:
            return False

    def read_field_descriptions_from_parquet(self, file_path: str) -> dict[str, str]:
        """
        Read field descriptions from column metadata stored in a Parquet file.

        :param file_path: Path to the Parquet file in the filesystem
        :return: A dictionary of field names and their descriptions
        """
        result = {}
        # Use pyarrow to read the schema from the parquet file
        with self.filesystem.open(file_path, "rb") as f:
            schema = pq.read_table(f).schema
            for name in schema.names:
                field = schema.field(name)
                if field.metadata and b"comment" in field.metadata:
                    result[name] = field.metadata[b"comment"].decode("utf-8")
        return result

    def read_geo_data_frame(self, file_path: str) -> gpd.GeoDataFrame:
        """
        Read a GeoDataFrame from a file in the workspace filesystem.

        :param file_path: Path to the file in the filesystem
        :raises ValueError: if the file can not be read
        :return: the GeoDataFrame
        """
        try:
            if self.is_parquet_file(file_path):
                with self.filesystem.open(file_path, "rb") as f:
                    gdf = gpd.read_parquet(f)

                # Add column descriptions as attributes
                gdf.attrs["column-descriptions"] = self.read_field_descriptions_from_parquet(file_path)
            else:
                with self.filesystem.open(file_path, "rb") as f:
                    gdf = gpd.read_file(f)

            if gdf is None:
                raise ValueError(f"Unable to create GeoDataFrame from: {os.path.basename(file_path)}")

            return gdf
        except Exception as e:
            logger.info(f"Unable to create GeoDataFrame from: {os.path.basename(file_path)}", e)
            raise ValueError(f"Unable to create GeoDataFrame from: {os.path.basename(file_path)}")

    def write_geo_data_frame(self, dataset_path: str, dataset_gdf: gpd.GeoDataFrame) -> None:
        """
        Write a GeoDataFrame as a parquet file in the workspace filesystem.

        :param dataset_path: Path in the filesystem for the output file
        :param dataset_gdf: the dataset to write
        """
        # Make sure the directory exists
        self.filesystem.makedirs(os.path.dirname(dataset_path), exist_ok=True)

        # Write the GeoDataFrame to parquet
        dataset_gdf.to_parquet(dataset_path, filesystem=self.filesystem)
