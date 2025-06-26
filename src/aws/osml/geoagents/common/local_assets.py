#  Copyright 2025 Amazon.com, Inc. or its affiliates.
import logging
import os
from typing import Dict, Tuple
from urllib.parse import urlparse

from pystac import Item

from .georeference import Georeference
from .workspace import Workspace

logger = logging.getLogger(__name__)


class LocalAssets:
    """
    A context manager that resolves URLs for STAC item assets into paths useable by the
    workspace filesystem.

    Example usage:
        with LocalAssets(dataset_georef, workspace) as (item, workspace_paths):
            # Reference the assets directly
            workspace_path = local_asset_paths[dataset_georef.asset_tag]
            # Process the data...

    """

    def __init__(self, georef: Georeference, workspace: Workspace):
        """
        Initialize the context manager.

        :param georef: The georeference for the STAC item to use
        :param workspace: The workspace containing the STAC item
        """
        self.georef = georef
        self.workspace = workspace
        self.item = None
        self.asset_paths: Dict[str, str] = {}

    def __enter__(self) -> Tuple[Item, Dict[str, str]]:
        """
        Enter the context, resolving the location of any assets to the workspace filesystem.

        :return: A tuple of (item, asset_paths) where item is the STAC item and
                asset_paths is a dictionary mapping asset keys to local file paths
        """
        self.item, self.asset_paths = LocalAssets.resolve_reference_to_assets(self.georef, self.workspace)
        return self.item, self.asset_paths

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exiting the resource manager currently has no effect. This may change in the future if
        we add in the ability for this class to download STAC items from a remote catalog.

        :param exc_type: The type of any exception that occurred
        :param exc_val: The instance of any exception that occurred
        :param exc_tb: The traceback of any exception that occurred
        """

    @staticmethod
    def resolve_reference_to_assets(dataset_georef: Georeference, workspace: Workspace) -> Tuple[Item, dict[str, str]]:
        """
        Convert any asset URLs to paths to the asset in the local workspace.

        :param dataset_georef: the georeference for the dataset
        :param workspace: the shared workspace
        :raises ValueError: if the dataset can not be downloaded from the workspace
        :return: a tuple of the STAC item and a map of selected asset keys to local paths
        """
        item = None
        local_asset_paths = {}
        try:
            item = workspace.get_item(dataset_georef)
            if not item:
                raise ValueError(f"Unable to find dataset {dataset_georef} in the workspace.")

            # Filter assets if selected_asset_keys is provided
            selected_asset_keys = [dataset_georef.asset_tag] if dataset_georef.asset_tag else None
            assets_to_access = item.assets
            if selected_asset_keys:
                assets_to_access = {k: v for k, v in item.assets.items() if k in selected_asset_keys}

            for asset_key, asset in assets_to_access.items():
                try:
                    # Parse the URL for the asset
                    parsed_url = urlparse(asset.href)
                    if parsed_url.scheme:
                        local_asset_paths[asset_key] = asset.href
                    else:
                        local_asset_paths[asset_key] = (
                            f"{workspace.prefix}/{item.id}/{asset_key}/{os.path.basename(asset.href)}"
                        )

                except Exception:
                    logger.warning(f"Error accessing {asset_key}", exc_info=True)
                    continue

        except Exception as e:
            logger.info(f"Unable to download dataset: {dataset_georef}", e)
            raise ValueError(f"Unable to access the dataset: {dataset_georef} in the shared workspace.")
        return item, local_asset_paths
