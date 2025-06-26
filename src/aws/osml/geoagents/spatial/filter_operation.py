#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
import tempfile
from pathlib import Path

import shapely

from ..common import Georeference, LocalAssets, Workspace
from .spatial_utils import create_derived_stac_item

logger = logging.getLogger(__name__)


def filter_operation(
    dataset_georef: Georeference, filter_bounds: shapely.Geometry, workspace: Workspace, function_name: str
) -> str:
    """
    Filter a dataset to only contain features that intersect a given geometry.

    :param dataset_georef: Georeference for the dataset to filter
    :param filter_bounds: Geometry to use as a filter
    :param workspace: Workspace for storing assets
    :param function_name: Function name for creating georeference
    :return: A formatted string with the filtering result
    :raises ValueError: If filtering fails
    """
    filtered_dataset_path = None

    try:
        # Use context manager to handle local assets
        with LocalAssets(dataset_georef, workspace) as (item, local_asset_paths):
            # Select the assets to process and load them into memory
            selected_asset_key = next(iter(local_asset_paths))
            local_dataset_path = local_asset_paths[selected_asset_key]
            gdf = workspace.read_geo_data_frame(str(local_dataset_path))

            # Run the filter operation
            filtered_gdf = gdf[gdf.intersects(filter_bounds)]

            # Generate summary text describing the result
            filtered_dataset_title = f"Filtered {item.properties['title']}"
            filtered_dataset_summary = (
                f"This dataset contains {len(filtered_gdf)} features selected from "
                f"{dataset_georef} because they were within the boundary of "
                f"{filter_bounds}. "
            )

            # Write the derived dataset to the local workspace cache
            filtered_dataset_reference = Georeference.new_from_timestamp(asset_tag=selected_asset_key, prefix=function_name)

            # Create a temporary directory for the filtered dataset
            temp_dir = Path(tempfile.gettempdir())
            filtered_dataset_path = temp_dir / filtered_dataset_reference.item_id / "filtered-result.parquet"
            filtered_dataset_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the filtered dataset
            workspace.write_geo_data_frame(str(filtered_dataset_path), filtered_gdf)

            # Create a new STAC item describing the result
            filtered_dataset_item = create_derived_stac_item(
                filtered_dataset_reference, filtered_dataset_title, filtered_dataset_summary, item
            )

            # Publish the result to the workspace
            workspace.create_item(item=filtered_dataset_item, temp_assets={selected_asset_key: filtered_dataset_path})

            # Generate text for final summary including counts and references
            text_result = (
                f"The dataset {dataset_georef} has been filtered. "
                f"The filtered result is known as {filtered_dataset_reference}. "
                f"A summary of the contents is: {filtered_dataset_summary}"
            )

            return text_result

    except Exception as e:
        logger.error("An error occurred during filter operation")
        logger.exception(e)
        raise ValueError(f"Unable to filter the dataset: {str(e)}")
    finally:
        # Remove the filtered dataset file
        if filtered_dataset_path and filtered_dataset_path.exists():
            filtered_dataset_path.unlink()
