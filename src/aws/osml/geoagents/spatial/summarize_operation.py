#  Copyright 2025-2026 Amazon.com, Inc. or its affiliates.

import logging

from pandas.api.types import (
    is_bool_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
    is_string_dtype,
)

from ..common import GeoDataReference, LocalAssets, Workspace
from .spatial_utils import load_geo_data_frame

logger = logging.getLogger(__name__)


def summarize_operation(dataset_reference: GeoDataReference, workspace: Workspace) -> str:
    """
    Generate a natural language description of columns in a geodataset.

    :param dataset_reference: GeoDataReference for the dataset to summarize
    :param workspace: Workspace for storing assets
    :return: A formatted string with the dataset summary
    :raises ValueError: If summarization fails
    """
    try:
        # Use context manager to handle local assets
        with LocalAssets(dataset_reference, workspace) as (item, local_asset_paths):
            # Load the dataset using the utility function
            gdf, item, selected_asset_key = load_geo_data_frame(local_asset_paths, workspace, dataset_reference, item)

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
                        metadata = f" ({gdf.attrs['column-descriptions'][col]})"

                    # Generate description based on data type
                    # NOTE: dtype string representations can vary by pandas/numpy versions
                    # (e.g., "object" vs StringDtype vs python "str"; datetime64[ns] vs [us]).
                    # Use pandas type helpers to keep output stable across environments.
                    if is_object_dtype(col_type) or is_string_dtype(col_type):
                        desc = f"{col}: General column{metadata}"
                    # Note: boolean dtypes are sometimes considered "numeric" by pandas helpers,
                    # so handle them before the numeric check to keep output stable.
                    elif is_bool_dtype(col_type):
                        desc = f"{col}: Boolean column{metadata}"
                    elif is_numeric_dtype(col_type):
                        # Preserve prior behavior: only summarize ranges for int64/float64.
                        # Other numeric dtypes (e.g., int32) are rendered as "Column of type ..."
                        # to keep output stable for existing expectations.
                        if str(col_type) in {"int64", "float64"}:
                            min_val = gdf[col].min()
                            max_val = gdf[col].max()
                            desc = f"{col}: Numeric column ({col_type}) ranging from {min_val} to {max_val}{metadata}"
                        else:
                            desc = f"{col}: Column of type {col_type}{metadata}"
                    elif is_datetime64_any_dtype(col_type):
                        desc = f"{col}: Date/time column{metadata}"
                    else:
                        desc = f"{col}: Column of type {col_type}{metadata}"

                    column_descriptions.append(desc)

        # Generate the final summary text
        summary = (
            f"Dataset {dataset_reference} contains {len(gdf)} features.\n"
            f"- {bbox_desc}\n"
            "Columns:\n" + "\n".join(f"- {desc}" for desc in column_descriptions)
        )

        return summary

    except Exception as e:
        logger.error("An error occurred during summarize operation")
        logger.exception(e)
        raise ValueError(f"Unable to summarize the dataset: {str(e)}")
