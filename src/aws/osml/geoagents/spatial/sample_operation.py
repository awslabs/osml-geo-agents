#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
from typing import Any, Optional

from ..common import GeoDataReference, LocalAssets, Workspace
from .spatial_utils import create_stac_item_for_dataset

logger = logging.getLogger(__name__)


def _truncate_value(value: Any, max_width: int) -> str:
    """
    Truncate a value to fit within max_width characters.

    :param value: The value to truncate
    :param max_width: Maximum width in characters
    :return: Truncated string representation
    """
    str_value = str(value)
    if len(str_value) > max_width:
        return str_value[: max_width - 3] + "..."
    return str_value


def sample_operation(
    dataset_reference: GeoDataReference,
    number_of_features: Optional[float],
    workspace: Workspace,
    max_column_width: int = 20,
) -> str:
    """
    Return a text representation of features from a geodataset.

    :param dataset_reference: GeoDataReference for the dataset to sample
    :param number_of_features: Number of features to sample (default: 10, maximum: 20)
    :param workspace: Workspace for storing assets
    :param max_column_width: Maximum width for each column in the table (default: 20)
    :return: A formatted string with the sampled features as a Markdown table
    :raises ValueError: If sampling fails
    """
    try:
        # Default to 10 features if not specified, cap at 20
        num_features = 10 if number_of_features is None else min(int(number_of_features), 20)

        # Use context manager to handle local assets
        with LocalAssets(dataset_reference, workspace) as (item, local_asset_paths):
            # Select the assets to process and load them into memory
            selected_asset_key = next(iter(local_asset_paths))
            local_dataset_path = local_asset_paths[selected_asset_key]
            gdf = workspace.read_geo_data_frame(str(local_dataset_path))

            # If item is None, create a new item from the GeoDataFrame
            if item is None:
                item = create_stac_item_for_dataset(
                    gdf,
                    str(local_dataset_path),
                    title=f"Dataset from {dataset_reference}",
                    description=f"Dataset loaded from {dataset_reference}",
                )

            # Get the requested number of features
            sampled_gdf = gdf.head(num_features)

            # Generate a text representation of the features
            total_features = len(gdf)
            sample_size = len(sampled_gdf)

            # Create header with dataset info
            text_result = [
                f"Sample of {sample_size} feature{'s' if sample_size != 1 else ''} "
                f"from dataset {dataset_reference} (total features: {total_features})\n"
            ]

            # Get column names
            columns = sampled_gdf.columns.tolist()

            # Format as markdown table
            # Create header row
            header_row = "| " + " | ".join(_truncate_value(col, max_column_width) for col in columns) + " |"
            text_result.append(header_row)

            # Create separator row
            separator_row = (
                "| " + " | ".join("-" * min(len(_truncate_value(col, max_column_width)), 10) for col in columns) + " |"
            )
            text_result.append(separator_row)

            # Add data rows
            for _, row in sampled_gdf.iterrows():
                data_row = "| " + " | ".join(_truncate_value(row[col], max_column_width) for col in columns) + " |"
                text_result.append(data_row)

            return "\n".join(text_result)

    except Exception as e:
        logger.error("An error occurred during sample operation")
        logger.exception(e)
        raise ValueError(f"Unable to sample the dataset: {str(e)}")
