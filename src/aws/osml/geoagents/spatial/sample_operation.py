#  Copyright 2025-2026 Amazon.com, Inc. or its affiliates.

import logging
import math
import numbers
from typing import Any, Optional

from ..common import GeoDataReference, LocalAssets, Workspace
from .spatial_utils import load_geo_data_frame

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


def _is_missing(value: Any) -> bool:
    """
    Return True if a value should be treated as missing/null.

    Handles None, NaN (Python and NumPy float), and pandas' NAType by name
    without importing pandas.
    """
    if value is None:
        return True

    # pandas.NA shows up as NAType; avoid importing pandas just to check it.
    if type(value).__name__ == "NAType":
        return True

    # Explicit numeric NaN handling (covers NumPy scalars too).
    # Note: bool is a numbers.Real, but it's never "NaN".
    if isinstance(value, bool):
        return False

    if isinstance(value, numbers.Real):
        try:
            return math.isnan(float(value))
        except Exception:
            return False

    # Complex numbers can contain NaN components.
    if isinstance(value, numbers.Complex):
        try:
            return math.isnan(float(value.real)) or math.isnan(float(value.imag))
        except Exception:
            return False

    return False


def _is_numeric_dtype(column_dtype: Any) -> bool:
    """
    Best-effort numeric dtype check without importing pandas.

    Works for NumPy/pandas dtypes (via .kind). We intentionally *exclude* boolean.
    """
    kind = getattr(column_dtype, "kind", None)
    if isinstance(kind, str):
        return kind in {"i", "u", "f", "c"}

    return False


def _format_cell(value: Any, column_dtype: Any) -> str:
    """
    Format a cell value for stable Markdown output.

    - For missing values in non-numeric columns, render as "None"
    - For missing values in numeric columns, render as "nan" (matches existing expectations)
    """
    if _is_missing(value):
        return "nan" if _is_numeric_dtype(column_dtype) else "None"
    return str(value)


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
            # Load the dataset using the utility function
            gdf, item, selected_asset_key = load_geo_data_frame(local_asset_paths, workspace, dataset_reference, item, None)

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
                data_row = (
                    "| "
                    + " | ".join(
                        _truncate_value(_format_cell(row[col], sampled_gdf[col].dtype), max_column_width) for col in columns
                    )
                    + " |"
                )
                text_result.append(data_row)

            return "\n".join(text_result)

    except Exception as e:
        logger.error("An error occurred during sample operation")
        logger.exception(e)
        raise ValueError(f"Unable to sample the dataset: {str(e)}")
