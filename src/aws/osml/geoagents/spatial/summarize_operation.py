#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging

from ..common import Georeference, LocalAssets, Workspace

logger = logging.getLogger(__name__)


def summarize_operation(dataset_georef: Georeference, workspace: Workspace) -> str:
    """
    Generate a natural language description of columns in a geodataset.

    :param dataset_georef: Georeference for the dataset to summarize
    :param workspace: Workspace for storing assets
    :return: A formatted string with the dataset summary
    :raises ValueError: If summarization fails
    """
    try:
        # Use context manager to handle local assets
        with LocalAssets(dataset_georef, workspace) as (item, local_asset_paths):
            # Select the assets to process and load them into memory
            selected_asset_key = next(iter(local_asset_paths))
            local_dataset_path = local_asset_paths[selected_asset_key]
            gdf = workspace.read_geo_data_frame(str(local_dataset_path))

            # Get the bounding box
            bounds = gdf.total_bounds
            bbox_desc = f"Dataset bounds (min_x, min_y, max_x, max_y): {bounds[0]:.6f}, {bounds[1]:.6f}, {bounds[2]:.6f}, {bounds[3]:.6f}"

            # Generate column descriptions
            column_descriptions = []

            # First describe the active geometry column
            if gdf.active_geometry_name is not None:
                geom_types = gdf[gdf.active_geometry_name].geom_type.unique()
                geom_desc = f"{gdf.active_geometry_name}: Contains spatial features of type(s): {', '.join(geom_types)}"
                column_descriptions.append(geom_desc)

            # Then describe all other columns
            for col in gdf.columns:
                if col != gdf.active_geometry_name:
                    col_type = gdf[col].dtype

                    # Get column metadata if available
                    metadata = ""
                    if "column-descriptions" in gdf.attrs and col in gdf.attrs["column-descriptions"]:
                        metadata = f" ({gdf.attrs["column-descriptions"][col]})"

                    # Generate description based on data type
                    if col_type == "object":
                        desc = f"{col}: General column{metadata}"
                    elif col_type in ["int64", "float64"]:
                        min_val = gdf[col].min()
                        max_val = gdf[col].max()
                        desc = f"{col}: Numeric column ({col_type}) ranging from {min_val} to {max_val}{metadata}"
                    elif col_type == "bool":
                        desc = f"{col}: Boolean column{metadata}"
                    elif col_type == "datetime64[ns]":
                        desc = f"{col}: Date/time column{metadata}"
                    else:
                        desc = f"{col}: Column of type {col_type}{metadata}"

                    column_descriptions.append(desc)

        # Generate the final summary text
        summary = (
            f"Dataset {dataset_georef} contains {len(gdf)} features.\n"
            f"- {bbox_desc}\n"
            "Columns:\n" + "\n".join(f"- {desc}" for desc in column_descriptions)
        )

        return summary

    except Exception as e:
        logger.error("An error occurred during summarize operation")
        logger.exception(e)
        raise ValueError(f"Unable to summarize the dataset: {str(e)}")
