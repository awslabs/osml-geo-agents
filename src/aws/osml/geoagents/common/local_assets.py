#  Copyright 2025 Amazon.com, Inc. or its affiliates.
import logging
import os
import tempfile
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

from pystac import Item

from .geo_data_reference import GeoDataReference
from .stac_reference import STACReference
from .workspace import Workspace

logger = logging.getLogger(__name__)


class LocalAssets:
    """
    A context manager that resolves various types of geospatial references into paths useable by the
    workspace filesystem.

    Example usage:
        with LocalAssets(geo_data_ref, workspace) as (item, workspace_paths):
            # Reference the assets directly
            if "asset_key" in workspace_paths:
                workspace_path = workspace_paths["asset_key"]
            # Process the data...

    """

    def __init__(self, geo_data_ref: GeoDataReference, workspace: Workspace):
        """
        Initialize the context manager.

        :param geo_data_ref: The geospatial data reference to use
        :param workspace: The workspace containing the data
        """
        self.geo_data_ref = geo_data_ref
        self.workspace = workspace
        self.item = None
        self.asset_paths: Dict[str, str] = {}

    def __enter__(self) -> Tuple[Optional[Item], Dict[str, str]]:
        """
        Enter the context, resolving the location of any assets to the workspace filesystem.

        :return: A tuple of (item, asset_paths) where item is the STAC item (or None for non-STAC references)
                and asset_paths is a dictionary mapping asset keys to local file paths
        """
        self.item, self.asset_paths = LocalAssets.resolve_reference_to_assets(self.geo_data_ref, self.workspace)
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
    def resolve_reference_to_assets(
        geo_data_ref: GeoDataReference, workspace: Workspace
    ) -> Tuple[Optional[Item], dict[str, str]]:
        """
        Convert geospatial references to paths usable by the workspace filesystem.

        This method handles different types of references:
        - STAC references: Resolves to STAC item assets in the workspace
        - WKT references: Creates a temporary file with the WKT content
        - File path references: Uses the path directly

        :param geo_data_ref: the geospatial data reference
        :param workspace: the shared workspace
        :raises ValueError: if the reference cannot be resolved
        :return: a tuple of the STAC item (or None for non-STAC references) and a map of asset keys to local paths
        """
        item = None
        local_asset_paths = {}

        # Handle different reference types
        if geo_data_ref.is_stac_reference():
            # For STAC references, use the existing logic to get the item from workspace
            try:
                stac_ref = STACReference(geo_data_ref.reference_string)

                item = workspace.get_item(stac_ref)
                if not item:
                    raise ValueError(f"Unable to find dataset {geo_data_ref} in the workspace.")

                # Filter assets if asset tag is provided in the STAC reference
                selected_asset_keys = [stac_ref.asset_tag] if stac_ref.asset_tag else None
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
                            # Include collections in the path if present
                            collections_path = "/".join(stac_ref.collections) + "/" if stac_ref.collections else ""
                            local_asset_paths[asset_key] = (
                                f"{workspace.prefix}/{collections_path}{item.id}/{asset_key}/{os.path.basename(asset.href)}"
                            )
                    except Exception:
                        logger.warning(f"Error accessing {asset_key}", exc_info=True)
                        continue

            except Exception:
                logger.info(f"Unable to access STAC dataset: {geo_data_ref}", exc_info=True)
                raise ValueError(f"Unable to access the STAC dataset: {geo_data_ref} in the shared workspace.")

        elif geo_data_ref.is_wkt():
            # For WKT references, create a temporary file with the WKT content
            try:
                # Create a temporary file with .wkt extension
                temp_file = tempfile.NamedTemporaryFile(suffix=".wkt", delete=False)
                temp_path = temp_file.name

                # Write the WKT content to the file
                with open(temp_path, "w") as f:
                    f.write(geo_data_ref.reference_string)

                # Add the temporary file path to the asset paths
                local_asset_paths["wkt"] = temp_path

                logger.info(f"Created temporary WKT file at {temp_path}")
            except Exception as e:
                logger.error(f"Error creating temporary WKT file: {str(e)}", exc_info=True)
                raise ValueError(f"Unable to create temporary file for WKT reference: {str(e)}")

        elif geo_data_ref.is_file_path():
            # For file path references, resolve the path and use it
            try:
                file_path = LocalAssets._resolve_file_path(geo_data_ref.reference_string, workspace)
                # Use the basename as the asset key
                asset_key = os.path.basename(file_path)
                local_asset_paths[asset_key] = file_path

                logger.info(f"Using resolved file path: {file_path}")
            except Exception as e:
                logger.error(f"Error processing file path: {str(e)}", exc_info=True)
                raise ValueError(f"Unable to process file path reference: {str(e)}")

        else:
            # This should never happen as GeoDataReference validates the type during initialization
            raise ValueError(f"Unknown reference type for {geo_data_ref}")

        return item, local_asset_paths

    @staticmethod
    def _resolve_file_path(file_path: str, workspace: Workspace) -> str:
        """
        Resolve a file path reference to a full path.

        This method handles different types of file paths:
        - S3 URLs: Used directly
        - Absolute paths: Used directly
        - Relative paths with directory components: Combined with workspace prefix and checked for existence
        - Just filenames: Searched for in the workspace prefix

        :param file_path: The file path reference string
        :param workspace: The workspace object
        :raises ValueError: If the file cannot be found or if multiple matching files are found
        :return: The resolved file path
        """
        # If it's an S3 URL, use it directly
        if file_path.startswith("s3://"):
            return file_path

        # If it's an absolute path, use it directly
        if os.path.isabs(file_path):
            return file_path

        # Check if the path has directory components
        if os.path.dirname(file_path):
            # It's a relative path with directory components
            # Combine with workspace prefix and check existence
            full_path = f"{workspace.prefix}/{file_path}"
            if workspace.filesystem.exists(full_path):
                return full_path
            else:
                raise ValueError(f"File not found at path: {full_path}")
        else:
            # It's just a filename, search for it in the workspace
            filename = os.path.basename(file_path)
            matching_files = []

            # Recursively search for files with matching name
            try:
                # List all files in the workspace prefix recursively
                all_files = workspace.filesystem.find(workspace.prefix, maxdepth=None)

                # Filter for files with matching name
                for found_file in all_files:
                    if os.path.basename(found_file) == filename:
                        matching_files.append(found_file)

                if len(matching_files) == 1:
                    # Exactly one match found
                    return matching_files[0]
                elif len(matching_files) > 1:
                    # Multiple matches found
                    raise ValueError(
                        f"Multiple files with name '{filename}' found in workspace. "
                        f"Please provide a full path to specify which file to use."
                    )
                else:
                    # No matches found
                    raise ValueError(f"No file with name '{filename}' found in workspace.")
            except Exception as e:
                logger.error(f"Error searching for file '{filename}': {str(e)}", exc_info=True)
                raise ValueError(f"Error searching for file '{filename}': {str(e)}")
