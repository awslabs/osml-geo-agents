#  Copyright 2025 Amazon.com, Inc. or its affiliates.
import logging
from pathlib import Path
from typing import Dict, Tuple

from pystac import Item

from .georeference import Georeference
from .tool_base import ToolExecutionError
from .workspace import Workspace

logger = logging.getLogger(__name__)


class LocalAssets:
    """
    A context manager for handling local copies of assets downloaded from a workspace.
    Automatically cleans up downloaded files when exiting the context.

    Example usage:
        with LocalAssets(dataset_georef, workspace) as (item, local_asset_paths):
            # Use the downloaded assets
            local_dataset_path = local_asset_paths[dataset_georef.asset_tag]
            # Process the data...

    The context manager will automatically clean up the downloaded files when exiting the context.
    """

    def __init__(self, georef: Georeference, workspace: Workspace):
        """
        Initialize the context manager.

        :param georef: The georeference for the assets to download
        :param workspace: The workspace to download assets from
        """
        self.georef = georef
        self.workspace = workspace
        self.item = None
        self.local_asset_paths: Dict[str, Path] = {}

    def __enter__(self) -> Tuple[dict, Dict[str, Path]]:
        """
        Enter the context, downloading the assets.

        :return: A tuple of (item, local_asset_paths) where item is the STAC item and
                local_asset_paths is a dictionary mapping asset keys to local file paths
        """
        self.item, self.local_asset_paths = LocalAssets.download_georef_from_workspace(self.georef, self.workspace)
        return self.item, self.local_asset_paths

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context, cleaning up downloaded files.

        :param exc_type: The type of any exception that occurred
        :param exc_val: The instance of any exception that occurred
        :param exc_tb: The traceback of any exception that occurred
        """
        if self.local_asset_paths:
            for asset_path in self.local_asset_paths.values():
                if asset_path.exists():
                    asset_path.unlink()

    @staticmethod
    def download_georef_from_workspace(dataset_georef: Georeference, workspace: Workspace) -> Tuple[Item, dict[str, Path]]:
        """
        Download a georeference from the workspace. This will download the STAC item and any assets.

        :param dataset_georef: the georeference for the dataset to download
        :param workspace: the shared workspace
        :raises ToolExecutionError: if the dataset can not be downloaded from the workspace
        :return: a tuple of the STAC item and a map of selected asset keys to local paths
        """
        try:
            item = workspace.get_item(dataset_georef)
            selected_asset_keys = [dataset_georef.asset_tag] if dataset_georef.asset_tag else None
            # TODO: Check to see what the estimated size of the dataset is. If it is large we will need
            #       to distribute processing to a cluster of workers. For now just assume it is small
            #       enough to process on the local machine.
            local_asset_paths = workspace.download_assets(item, selected_asset_keys)
        except Exception as e:
            logger.info(f"Unable to download dataset: {dataset_georef}", e)
            raise ToolExecutionError(f"Unable to access the dataset: {dataset_georef} in the shared workspace.")
        return item, local_asset_paths
