#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
from typing import Optional

from ..common import Georeference, LocalAssets, Workspace
from .spatial_utils import read_geo_data_frame

logger = logging.getLogger(__name__)


def sample_operation(dataset_georef: Georeference, number_of_features: Optional[float], workspace: Workspace) -> str:
    """
    Return a text representation of features from a geodataset.

    :param dataset_georef: Georeference for the dataset to sample
    :param number_of_features: Number of features to sample (default: 10)
    :param workspace: Workspace for storing assets
    :return: A formatted string with the sampled features
    :raises ValueError: If sampling fails
    """
    try:
        # Default to 10 features if not specified
        num_features = 10 if number_of_features is None else int(number_of_features)

        # Use context manager to handle local assets
        with LocalAssets(dataset_georef, workspace) as (item, local_asset_paths):
            # Select the assets to process and load them into memory
            selected_asset_key = next(iter(local_asset_paths))
            local_dataset_path = local_asset_paths[selected_asset_key]
            gdf = read_geo_data_frame(local_dataset_path)

            # Get the requested number of features
            sampled_gdf = gdf.head(num_features)

            # Generate a text representation of the features
            total_features = len(gdf)
            sample_size = len(sampled_gdf)

            # Create header with dataset info
            text_result = [
                f"Sample of {sample_size} feature{'s' if sample_size != 1 else ''} "
                f"from dataset {dataset_georef} (total features: {total_features})\n"
            ]

            # Add column names
            columns = sampled_gdf.columns.tolist()
            text_result.append("Columns: " + ", ".join(columns) + "\n")

            # Add feature data
            text_result.append("\nFeatures:")
            for idx, row in sampled_gdf.iterrows():
                text_result.append(f"\nFeature {idx}:")
                for col in columns:
                    text_result.append(f"  {col}: {row[col]}")

            return "\n".join(text_result)

    except Exception as e:
        logger.error("An error occurred during sample operation")
        logger.exception(e)
        raise ValueError(f"Unable to sample the dataset: {str(e)}")
