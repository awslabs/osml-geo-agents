#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import geopandas as gpd
import pyarrow.parquet as pq
from pystac import Asset, Item
from s3fs import S3FileSystem

from aws.osml.geoagents.common.stac_reference import STACReference

logger = logging.getLogger(__name__)


# This mapping is taken from geopandas. In theory the read/write file
# routines handle this natively but some issues have been observed
# working with binary streams.
_EXTENSION_TO_DRIVER = {
    ".bna": "BNA",
    ".dxf": "DXF",
    ".csv": "CSV",
    ".shp": "ESRI Shapefile",
    ".dbf": "ESRI Shapefile",
    ".json": "GeoJSON",
    ".geojson": "GeoJSON",
    ".geojsonl": "GeoJSONSeq",
    ".geojsons": "GeoJSONSeq",
    ".gpkg": "GPKG",
    ".gml": "GML",
    ".xml": "GML",
    ".gpx": "GPX",
    ".gtm": "GPSTrackMaker",
    ".gtz": "GPSTrackMaker",
    ".tab": "MapInfo File",
    ".mif": "MapInfo File",
    ".mid": "MapInfo File",
    ".dgn": "DGN",
    ".fgb": "FlatGeobuf",
}


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

        # Extract user_id from prefix if it's the last component
        self.user_id = os.path.basename(self.prefix) if self.prefix else "shared"

    def _is_s3_filesystem(self) -> bool:
        """
        Check if the filesystem is an S3FileSystem.

        :return: True if using S3FileSystem, False otherwise
        """
        return isinstance(self.filesystem, S3FileSystem)

    def _is_local_path(self, file_path: str) -> bool:
        """
        Check if a file path is a local filesystem path.

        Local paths include:
        - Absolute paths starting with / (e.g., /tmp/file.wkt)
        - Relative paths (e.g., ../data/file.txt, data/file.txt)

        S3 paths should use the s3:// URI format.

        :param file_path: Path to check
        :return: True if local path, False if S3 path
        """
        return file_path.startswith("/") or (not file_path.startswith("s3://"))

    def _safe_makedirs(self, dir_path: str) -> None:
        """
        Safely create directories, skipping the operation for S3 filesystems.

        S3 doesn't require directories to exist before writing objects - it treats
        paths as object keys, not directory structures. Calling makedirs on S3
        can cause permission errors as it tries to create buckets.

        :param dir_path: Directory path to create
        """
        if not self._is_s3_filesystem():
            # Only create directories for non-S3 filesystems
            self.filesystem.makedirs(dir_path, exist_ok=True)

    def _get_stac_item_base_path(self, item_id: str, collections: Optional[List[str]] = None) -> str:
        """
        Convert a STAC item ID and optional collections to a local base path.

        :param item_id: The ID of the STAC item
        :param collections: Optional list of collections this item belongs to
        :return: The base path for the STAC item
        """
        collections_path = "/".join(filter(None, collections)) + "/" if collections else ""
        return f"{self.prefix}/stac/{collections_path}{item_id}"

    def get_item(self, stac_ref: STACReference) -> Item:
        """
        This method returns the STAC Item (summary information) for a STAC reference.
        It retrieves this item directly from the filesystem but eventually should likely
        look the item up in the index for the STAC.

        :param stac_ref: the STAC reference to retrieve
        :return: the STAC item
        """
        # Get the base path for the item
        item_base_path = self._get_stac_item_base_path(stac_ref.item_id, stac_ref.collections)
        item_path = f"{item_base_path}/item.json"

        try:
            # Get the item JSON from the filesystem
            with self.filesystem.open(item_path, "rb") as f:
                item_data = json.loads(f.read().decode("utf-8"))
                return Item.from_dict(item_data)
        except Exception as e:
            raise Exception(f"Failed to retrieve item from filesystem: {str(e)}") from e

    def list_items(self) -> List[STACReference]:
        """
        List all items in the workspace.

        :return: a list of STACReference objects for each item
        """
        try:
            # Use filesystem's ls method to list directories
            stac_refs: List[STACReference] = []

            # List all directories under the stac directory
            stac_dir = f"{self.prefix}/stac"
            try:
                # Check if the stac directory exists
                if self.filesystem.exists(stac_dir):
                    # Get all directories at the stac directory level
                    dirs = self.filesystem.ls(stac_dir, detail=True)

                    # Filter for directories only
                    dirs = [d for d in dirs if d.get("type", None) == "directory"]

                    for directory in dirs:
                        # Extract the path components
                        dir_path = directory["name"]
                        # Start with an empty collections list
                        self._process_directory(dir_path, [], stac_refs)
            except FileNotFoundError:
                # If the stac directory doesn't exist yet, return an empty list
                pass

            return stac_refs
        except Exception as e:
            logger.warning(f"Error listing items: {str(e)}")
            raise Exception(f"Failed to list items: {str(e)}")

    def _process_directory(self, dir_path: str, current_collections: List[str], stac_refs: List[STACReference]) -> None:
        """
        Recursively process directories to find STAC items and their collections.

        :param dir_path: The directory path to process
        :param current_collections: The current list of collections in the path
        :param stac_refs: The list to add found STACReference objects to
        """
        # Check if this directory contains an item.json file
        item_json_path = f"{dir_path}/item.json"
        if self.filesystem.exists(item_json_path):
            # This is an item directory, extract the item ID
            item_id = os.path.basename(dir_path.rstrip("/"))
            # Create a STACReference with the current collections
            stac_refs.append(STACReference.from_parts(item_id=item_id, collections=current_collections.copy()))
            return

        # If not an item directory, check for subdirectories that might be collections or items
        try:
            subdirs = self.filesystem.ls(dir_path, detail=True)
            subdirs = [d for d in subdirs if d.get("type", None) == "directory"]

            for subdir in subdirs:
                subdir_path = subdir["name"]
                subdir_name = os.path.basename(subdir_path.rstrip("/"))

                # Check if this subdirectory contains an item.json file
                subdir_item_json_path = f"{subdir_path}/item.json"
                if self.filesystem.exists(subdir_item_json_path):
                    # This is an item directory, extract the item ID
                    item_id = subdir_name
                    # Create a STACReference with the current collections
                    stac_refs.append(STACReference.from_parts(item_id=item_id, collections=current_collections.copy()))
                else:
                    # This is a collection directory, process it recursively
                    new_collections = current_collections.copy()
                    new_collections.append(subdir_name)
                    self._process_directory(subdir_path, new_collections, stac_refs)
        except FileNotFoundError:
            # If directory doesn't exist or can't be listed, just return
            pass
        except Exception as e:
            logger.warning(f"Error listing items: {str(e)}")
            raise Exception(f"Failed to list items: {str(e)}")

    def delete_item(self, stac_ref: STACReference) -> None:
        """
        Delete an item and all its assets from the workspace.

        :param stac_ref: the STAC reference of the item to delete
        :raises Exception: if the item cannot be deleted
        """
        # Get the base path for the item
        item_path = self._get_stac_item_base_path(stac_ref.item_id, stac_ref.collections)

        try:
            # Check if the item exists
            if self.filesystem.exists(item_path):
                # Use recursive delete to remove the item directory and all contents
                self.filesystem.rm(item_path, recursive=True)
                logger.info(f"Deleted item {stac_ref}")
            else:
                logger.warning(f"No objects found for item {stac_ref}")
        except Exception as e:
            logger.warning(f"Error deleting item {stac_ref}: {str(e)}")
            raise Exception(f"Failed to delete item {stac_ref}: {str(e)}")

    def create_item(
        self, item: Item, temp_assets: Optional[Dict[str, Path]], collections: Optional[List[str]] = None
    ) -> STACReference:
        """
        Create an item/assets in the workspace.

        The item itself does not need to have an array of assets defined. Instead, an optional dictionary that
        maps asset keys to temporary paths will be used to create assets. Each temporary file will be transferred to the
        filesystem for the workspace and then the STAC Item asset hrefs will be updated to point to those
        locations.

        :param item: the STAC item to create
        :param temp_assets: a mapping of asset keys to local files
        :param collections: optional list of collections this item belongs to
        :return: the STAC reference for the new item
        """
        # Get the base path for this item
        item_base_path = self._get_stac_item_base_path(item.id, collections)

        if temp_assets:
            for asset_key, local_path in temp_assets.items():
                try:
                    # Construct path for the asset in the filesystem
                    asset_path = f"{item_base_path}/{asset_key}/{local_path.name}"

                    # Make sure the directory exists
                    self._safe_makedirs(os.path.dirname(asset_path))

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
            self._safe_makedirs(os.path.dirname(item_json_path))

            # Upload item JSON to the filesystem
            with self.filesystem.open(item_json_path, "w") as f:
                f.write(item_json)
        except Exception as e:
            logger.warning(f"\nError uploading {item_json_path}: {str(e)}")
            raise Exception(f"Failed to upload item JSON: {str(e)}")

        # Create and return STACReference
        return STACReference.from_parts(item_id=item.id, collections=collections)

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

    def read_wkt_file(self, file_path: str) -> gpd.GeoDataFrame:
        """
        Read a WKT file and convert it to a GeoDataFrame.

        :param file_path: Path to the WKT file in the filesystem
        :return: A GeoDataFrame created from the WKT data with CRS set to EPSG:4326
        """
        try:
            if self._is_local_path(file_path):
                # Use local filesystem for local paths (e.g., /tmp/file.wkt)
                with open(file_path, "r") as f:
                    wkt_data = f.read()
            else:
                # Use workspace S3 filesystem for S3 paths
                with self.filesystem.open(file_path, "r") as f:
                    wkt_data = f.read()

            # Create a GeoSeries from the WKT strings
            geo_series = gpd.GeoSeries.from_wkt([wkt_data])

            # Create a GeoDataFrame with the GeoSeries as the geometry column
            gdf = gpd.GeoDataFrame(geometry=geo_series)

            # Set the CRS to EPSG:4326 as specified
            gdf.set_crs(epsg=4326, inplace=True)

            return gdf
        except Exception:
            logger.error(f"Unable to create GeoDataFrame from WKT file: {os.path.basename(file_path)}", exc_info=True)
            raise ValueError(f"Unable to create GeoDataFrame from WKT file: {os.path.basename(file_path)}")

    def read_geo_data_frame(self, dataset_path: str) -> gpd.GeoDataFrame:
        """
        Read a GeoDataFrame from a file in the workspace filesystem.

        :param file_path: Path to the file in the filesystem
        :raises ValueError: if the file can not be read
        :return: the GeoDataFrame
        """
        try:
            # Check if this is a WKT file
            if dataset_path.lower().endswith(".wkt"):
                return self.read_wkt_file(dataset_path)
            elif self.is_parquet_file(dataset_path):
                with self.filesystem.open(dataset_path, "rb") as f:
                    gdf = gpd.read_parquet(f)

                # Add column descriptions as attributes
                gdf.attrs["column-descriptions"] = self.read_field_descriptions_from_parquet(dataset_path)
            else:
                # Determine the driver based on file extension
                _, ext = os.path.splitext(dataset_path.lower())
                driver = _EXTENSION_TO_DRIVER.get(ext)

                # This is a hack to work around some compatability issues between
                # GeoPandas / pyogrio and the fsspec based filesystem used by the
                # workspace. pyogrio is using GDAL libraries under the cover and
                # those are not working well with the file like objects that
                # result from the fsspec open calls. This hack copies the geo
                # file to a local temporary file which can then be read successfully
                # by the pyogrio library.
                with tempfile.NamedTemporaryFile(suffix=ext) as temp_file:
                    with self.filesystem.open(dataset_path, "rb") as f:
                        temp_file.write(f.read())
                        temp_file.flush()

                    # Read from the temporary file with the appropriate driver
                    gdf = gpd.read_file(temp_file.name, driver=driver)

            if gdf is None:
                raise ValueError(f"Unable to create GeoDataFrame from: {os.path.basename(dataset_path)}")

            return gdf
        except Exception:
            logger.error(f"Unable to create GeoDataFrame from: {os.path.basename(dataset_path)}", exc_info=True)
            raise ValueError(f"Unable to create GeoDataFrame from: {os.path.basename(dataset_path)}")

    def combine_geometry_columns(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Create a copy of the GeoDataFrame with all geometry columns combined into one.

        When a GeoDataFrame has multiple geometry columns, this function creates a copy
        that combines all geometry columns into a single GeometryCollection and sets
        this as the only geometry column in the result. If there's only one geometry
        column, the original GeoDataFrame is returned unchanged.

        This function ensures that any nested GeometryCollections are flattened before
        adding them to the final GeometryCollection.

        :param gdf: Input GeoDataFrame that may have multiple geometry columns
        :return: A GeoDataFrame with only a single geometry column
        """
        geometry_cols = gdf.columns[gdf.dtypes == "geometry"]

        if len(geometry_cols) <= 1:
            return gdf

        result_gdf = gdf.copy()
        active_geom_col = gdf.geometry.name

        # Combine all geometry columns into a GeometryCollection
        from shapely.geometry import GeometryCollection

        def flatten_geometry_collection(geom):
            """
            Recursively flatten a geometry, extracting all geometries from nested GeometryCollections.

            :param geom: A shapely geometry object that might be a GeometryCollection
            :return: A list of non-GeometryCollection geometries
            """
            if geom is None:
                return []

            if isinstance(geom, GeometryCollection):
                # Recursively flatten each geometry in the collection
                flattened = []
                for g in geom.geoms:
                    flattened.extend(flatten_geometry_collection(g))
                return flattened
            else:
                # Return non-GeometryCollection geometries as-is
                return [geom]

        # Create a new geometry column with flattened GeometryCollection for each row
        def combine_geometries(row):
            # Get all non-None geometries from geometry columns
            all_geometries = []
            for col in geometry_cols:
                if row[col] is not None:
                    # Flatten any nested GeometryCollections
                    all_geometries.extend(flatten_geometry_collection(row[col]))

            # Create a new GeometryCollection with the flattened geometries
            return GeometryCollection(all_geometries) if all_geometries else None

        # Apply the function to create combined geometries
        result_gdf[active_geom_col] = result_gdf.apply(combine_geometries, axis=1)

        # Drop all other geometry columns
        cols_to_drop = [col for col in geometry_cols if col != active_geom_col]
        if cols_to_drop:
            result_gdf = result_gdf.drop(columns=cols_to_drop)

        return result_gdf

    def write_geo_data_frame(self, dataset_path: str, dataset_gdf: gpd.GeoDataFrame) -> None:
        """
        Write a GeoDataFrame to the workspace filesystem.

        This function supports multiple output formats (Parquet, GeoJSON, etc.).
        The format will be chosen to match the file extension on the dataset path. Common
        extensions include .parquet and .geojson to generate GeoParquet and GeoJSON files
        respectively. Other extensions (.xml, .csv, etc.) are supported as well but depend
        on GeoPandas.

        For paths within the temp_dir, writes directly to local filesystem.
        For workspace paths, uses the workspace filesystem (local or S3).

        :param dataset_path: Path in the filesystem for the output file
        :param dataset_gdf: the dataset to write
        """
        # Make sure the directory exists
        self._safe_makedirs(os.path.dirname(dataset_path))

        # Determine if this is a temp file (local) or workspace file
        # Temp files start with system temp directory (e.g., /tmp)

        is_temp_file = str(dataset_path).startswith(tempfile.gettempdir())

        # Check file extension to determine write method
        if dataset_path.lower().endswith((".parquet", ".geoparquet")):
            if is_temp_file:
                # Write temp files directly to local filesystem
                dataset_gdf.to_parquet(dataset_path)
            else:
                # Write workspace files using workspace filesystem
                dataset_gdf.to_parquet(dataset_path, filesystem=self.filesystem)
        else:
            # Determine the driver based on file extension
            _, ext = os.path.splitext(dataset_path.lower())
            driver = _EXTENSION_TO_DRIVER.get(ext)

            # Handle GeoJSON format specifically for multiple geometry columns
            is_geojson = ext.lower() in [".json", ".geojson"]
            write_gdf = dataset_gdf

            # Check if we're writing to GeoJSON and have multiple geometry columns
            if is_geojson:
                # Use the utility function to combine geometry columns if needed
                write_gdf = self.combine_geometry_columns(dataset_gdf)
                if write_gdf is not dataset_gdf:  # Only log if we actually made a change
                    logger.info(
                        f"Multiple geometry columns detected. Combining all geometry columns for {os.path.basename(dataset_path)}"
                    )

            if is_temp_file:
                # Write temp files directly to local filesystem
                write_gdf.to_file(dataset_path, driver=driver)
            else:
                # For workspace files, use temp file workaround for fsspec compatibility
                # This is a hack to work around compatibility issues between
                # GeoPandas/pyogrio and the fsspec based filesystem used by the
                # workspace. pyogrio uses GDAL libraries which don't work well with
                # file-like objects from fsspec open calls.
                with tempfile.NamedTemporaryFile(suffix=ext) as temp_file:
                    write_gdf.to_file(temp_file.name, driver=driver)

                    # Read the temporary file and write to the filesystem
                    with open(temp_file.name, "rb") as src:
                        with self.filesystem.open(dataset_path, "wb") as dst:
                            dst.write(src.read())
