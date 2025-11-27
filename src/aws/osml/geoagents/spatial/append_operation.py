#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
import tempfile
from pathlib import Path
from typing import List

import geopandas as gpd
import pandas as pd

from ..common import GeoDataReference, LocalAssets, STACReference, Workspace
from .spatial_utils import create_derived_stac_item, load_geo_data_frame

logger = logging.getLogger(__name__)


def append_operation(
    dataset_references: List[GeoDataReference], workspace: Workspace, function_name: str, output_format: str = "parquet"
) -> str:
    """
    Combine multiple geodataframes into a single result by appending them.

    :param dataset_references: List of GeoDataReferences for the datasets to combine
    :param workspace: Workspace for storing assets
    :param function_name: Function name for creating reference
    :param output_format: Format for the output file (geojson or parquet)
    :return: A formatted string with the append result
    :raises ValueError: If append fails or if no datasets are provided
    """
    append_dataset_path = None

    try:
        # Validate input parameters
        if not dataset_references:
            raise ValueError("At least one dataset must be provided")

        # Load all geodataframes
        gdfs = []
        items = []

        for reference in dataset_references:
            with LocalAssets(reference, workspace) as (item, local_assets):
                # Load the dataset using the utility function
                gdf, item, selected_asset_key = load_geo_data_frame(local_assets, workspace, reference, item)

                items.append(item)
                gdfs.append(gdf)

        # Append all geodataframes
        if not gdfs:
            raise ValueError("No valid geodataframes found in the provided references")

        # Use pd.concat to combine the geodataframes and convert the result back to a GeoDataFrame
        result_df = pd.concat(gdfs, ignore_index=True)
        result_gdf = gpd.GeoDataFrame(result_df, geometry=result_df.geometry.name, crs=gdfs[0].crs)

        # Generate summary text describing the result
        dataset_titles = [item.properties.get("title", f"Dataset {i + 1}") for i, item in enumerate(items)]
        append_dataset_title = f"Combined dataset from {len(dataset_titles)} sources"
        append_dataset_summary = (
            f"This dataset contains {len(result_gdf)} features resulting from appending "
            f"{len(dataset_references)} datasets: {', '.join(dataset_titles)}."
        )

        # Write the derived dataset to the local workspace cache
        stac_ref = STACReference.new_from_timestamp(asset_tag="combined", prefix=function_name)
        append_dataset_reference = GeoDataReference.from_stac_reference(stac_ref)

        # Create a temporary directory for the append dataset
        temp_dir = Path(tempfile.gettempdir())
        append_dataset_path = temp_dir / stac_ref.item_id / f"append-result.{output_format}"
        append_dataset_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the append dataset
        workspace.write_geo_data_frame(str(append_dataset_path), result_gdf)

        # Create a new STAC item describing the result
        append_dataset_item = create_derived_stac_item(
            append_dataset_reference, append_dataset_title, append_dataset_summary, items[0]
        )

        # Publish the result to the workspace
        workspace.create_item(item=append_dataset_item, temp_assets={"combined": append_dataset_path})

        # Generate text for final summary including counts and references
        text_result = (
            f"The {len(dataset_references)} datasets have been combined into a single dataset. "
            f"The combined result is known as {append_dataset_reference}. "
            f"A summary of the contents is: {append_dataset_summary}"
        )

        return text_result

    except Exception as e:
        logger.error("An error occurred during append operation")
        logger.exception(e)
        raise ValueError(f"Unable to append the datasets: {str(e)}")
    finally:
        # Remove the append dataset file
        if append_dataset_path and append_dataset_path.exists():
            append_dataset_path.unlink()
