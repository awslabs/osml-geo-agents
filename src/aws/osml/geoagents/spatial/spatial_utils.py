#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
from datetime import datetime
from pathlib import Path
from typing import Tuple

import geopandas as gpd
from pystac import Item

from ..common import Georeference, ToolExecutionError, Workspace

logger = logging.getLogger(__name__)


def is_parquet_file(file_path: Path) -> bool:
    """
    Check if a file is a Parquet file by reading the magic bytes at the beginning of the file.

    :param file_path: Path to the file to check
    :return: True if the file is a Parquet file, False otherwise
    """
    # Parquet files start with PAR1 magic bytes
    try:
        with open(file_path, "rb") as f:
            magic_bytes = f.read(4)
            return magic_bytes == b"PAR1"
    except Exception:
        return False


def read_geo_data_frame(file_path: Path) -> gpd.GeoDataFrame:
    """
    Read a GeoDataFrame from a file.

    :param file_path: Path to the file to read
    :raises ToolExecutionError: if the file can not be read
    :return: the GeoDataFrame
    """
    # TODO: Dig into this and understand how GeoPandas normally handles multiple file formats.
    #       Attempting to open a parquet file with .from_file results in a PROJ error.
    #       It is unclear if that error is a problem in the dependencies/docker build or
    #       if we need this level of checking to decide how to open different file formats.
    try:
        if is_parquet_file(file_path):
            gdf = gpd.read_parquet(file_path)
        else:
            gdf = gpd.GeoDataFrame.from_file(file_path)
        if gdf is None:
            raise ToolExecutionError(f"Unable to create GeoDataFrame from: {file_path.name}")
        return gdf
    except Exception as e:
        logger.info(f"Unable to create GeoDataFrame from: {file_path.name}", e)
        raise ToolExecutionError(f"Unable to create GeoDataFrame from: {file_path.name}")


def write_geo_data_frame(dataset_path: Path, dataset_gdf: gpd.GeoDataFrame) -> None:
    """
    Write a GeoDataFrame as a parquet file.

    :param dataset_path: the Path of the output file
    :param dataset_gdf: the dataset
    """
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    dataset_gdf.to_parquet(dataset_path)


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
        local_assets = workspace.download_assets(item, selected_asset_keys)
    except Exception as e:
        logger.info(f"Unable to download dataset: {dataset_georef}", e)
        raise ToolExecutionError(f"Unable to access the dataset: {dataset_georef} in the shared workspace.")
    return item, local_assets


def create_derived_stac_item(
    derived_dataset_reference: Georeference,
    derived_dataset_title: str,
    derived_dataset_description: str,
    original_item: Item,
):
    """
    Create a new STAC Item for the result dataset. The new item will duplicate information from the original
    item when meaningful.

    :param derived_dataset_reference: the new georeference for the derived dataset
    :param derived_datset_title: the title of the derived dataset
    :param derived_dataset_description: the description of the derived dataset
    :param original_item: the original item
    :return: a new STAC item for the derived dataset
    """

    start_datetime = None
    end_datetime = None
    if "start_datetime" in original_item.properties and "end_datetime" in original_item.properties:
        start_datetime = datetime.fromisoformat(original_item.properties["start_datetime"])
        end_datetime = datetime.fromisoformat(original_item.properties["end_datetime"])

    # TODO: Consider computing better geometry and bbox attributes for this derived STAC item.
    #       In theory the new bounds should be no bigger than the filter.

    filtered_dataset_item = Item(
        id=derived_dataset_reference.item_id,
        geometry=original_item.geometry,
        bbox=original_item.bbox,
        datetime=original_item.datetime,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        properties={
            "title": derived_dataset_title,
            "description": derived_dataset_description,
            "keywords": original_item.properties["keywords"],
        },
    )
    filtered_dataset_item.add_derived_from(original_item)
    return filtered_dataset_item
