#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
import tempfile
from enum import Enum
from pathlib import Path
from typing import Optional

import geopandas as gpd

from ..common import GeoDataReference, LocalAssets, STACReference, Workspace
from .spatial_utils import create_derived_stac_item, load_geo_data_frame

logger = logging.getLogger(__name__)


class FilterTypes(Enum):
    """Enumeration of supported filter types."""

    INTERSECTS = "intersects"
    DIFFERENCE = "difference"


def filter_operation(
    dataset_reference: GeoDataReference,
    filter_reference: GeoDataReference,
    filter_type: Optional[FilterTypes],
    workspace: Workspace,
    function_name: str,
    dataset_geo_column: Optional[str] = None,
    filter_geo_column: Optional[str] = None,
    output_format: str = "parquet",
) -> str:
    """
    Filter a dataset to only contain features based on their spatial relationship with another dataset.

    :param dataset_reference: GeoDataReference for the dataset to filter
    :param filter_reference: GeoDataReference for the dataset to use as a filter
    :param filter_type: Type of filter to apply (intersects or difference)
    :param workspace: Workspace for storing assets
    :param function_name: Function name for creating reference
    :param dataset_geo_column: Optional name of the geometry column in the dataset
    :param filter_geo_column: Optional name of the geometry column in the filter dataset
    :param output_format: Format for the output file (geojson or parquet)
    :return: A formatted string with the filtering result
    :raises ValueError: If filtering fails
    """
    filtered_dataset_path = None

    try:
        # Default to INTERSECTS if filter_type is not provided
        filter_type = filter_type if filter_type else FilterTypes.INTERSECTS

        # Use workspace to access the geospatial datasets
        with LocalAssets(dataset_reference, workspace) as (item, local_asset_paths), LocalAssets(
            filter_reference, workspace
        ) as (
            filter_item,
            filter_local_asset_paths,
        ):
            # Load the dataset using the utility function
            gdf, item, selected_asset_key = load_geo_data_frame(
                local_asset_paths, workspace, dataset_reference, item, dataset_geo_column
            )

            # Load the filter dataset using the utility function
            filter_gdf, filter_item, filter_asset_key = load_geo_data_frame(
                filter_local_asset_paths, workspace, filter_reference, filter_item, filter_geo_column
            )

            # Run the filter operation
            if filter_type == FilterTypes.INTERSECTS:
                # Perform spatial join to find features that intersect
                joined = gpd.sjoin(gdf, filter_gdf, how="inner")
                filtered_gdf = gpd.GeoDataFrame(joined.drop(columns=["index_right"]))
            else:  # FilterTypes.DIFFERENCE
                # Perform spatial join to find features that don't intersect
                joined = gpd.sjoin(gdf, filter_gdf, how="left")
                filtered_gdf = gpd.GeoDataFrame(joined[joined["index_right"].isna()].drop(columns=["index_right"]))

            # Generate summary text describing the result
            filtered_dataset_title = f"Filtered {item.properties['title']}"
            filtered_dataset_summary = (
                f"This dataset contains {len(filtered_gdf)} features selected from "
                f"{dataset_reference} using a {filter_type.value} filter against "
                f"{filter_reference}. "
            )

            # Write the derived dataset to the local workspace cache
            stac_ref = STACReference.new_from_timestamp(asset_tag=selected_asset_key, prefix=function_name)
            filtered_dataset_reference = GeoDataReference.from_stac_reference(stac_ref)

            # Create a temporary directory for the filtered dataset
            temp_dir = Path(tempfile.gettempdir())
            filtered_dataset_path = temp_dir / stac_ref.item_id / f"filtered-result.{output_format}"
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
                f"The dataset {dataset_reference} has been filtered. "
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
