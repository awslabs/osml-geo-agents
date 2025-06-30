#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
import tempfile
from enum import Enum
from pathlib import Path
from typing import Optional

import geopandas as gpd
from pyproj import CRS

from ..common import Georeference, LocalAssets, Workspace
from .spatial_utils import create_derived_stac_item, validate_dataset_crs

logger = logging.getLogger(__name__)


class CorrelationTypes(Enum):
    """Enumeration of supported correlation types."""

    INTERSECTION = "intersection"
    DIFFERENCE = "difference"


def correlation_operation(
    dataset1_georef: Georeference,
    dataset2_georef: Georeference,
    correlation_type: Optional[CorrelationTypes],
    distance: Optional[float],
    dataset1_geo_column: Optional[str],
    dataset2_geo_column: Optional[str],
    workspace: Workspace,
    function_name: str,
    output_format: str = "parquet",
) -> str:
    """
    Correlate two spatial datasets using a spatial join.

    :param dataset1_georef: Georeference for the first dataset
    :param dataset2_georef: Georeference for the second dataset
    :param correlation_type: Type of correlation to perform (intersection or difference)
    :param distance: Optional buffer distance in meters to apply to the first dataset
    :param dataset1_geo_column: Optional name of the geometry column in the first dataset
    :param dataset2_geo_column: Optional name of the geometry column in the second dataset
    :param workspace: Workspace for storing assets
    :param function_name: Function name for creating georeference
    :param output_format: Format for the output file (geojson or parquet)
    :return: A formatted string with the correlation result
    :raises ValueError: If correlation fails
    """
    correlation_dataset_path = None

    try:
        # Default to INTERSECTION if correlation_type is not provided
        correlation_type = correlation_type if correlation_type else CorrelationTypes.INTERSECTION

        # Use workspace to access the geospatial datasets
        with LocalAssets(dataset1_georef, workspace) as (item1, local_assets1), LocalAssets(dataset2_georef, workspace) as (
            item2,
            local_assets2,
        ):

            # Select the assets to process and load them into memory
            selected_asset_key1 = next(iter(local_assets1))
            local_dataset_path1 = local_assets1[selected_asset_key1]
            gdf1 = workspace.read_geo_data_frame(str(local_dataset_path1))
            if dataset1_geo_column:
                gdf1.set_geometry(dataset1_geo_column, inplace=True)
            validate_dataset_crs(gdf1, dataset1_georef)

            selected_asset_key2 = next(iter(local_assets2))
            local_dataset_path2 = local_assets2[selected_asset_key2]
            gdf2 = workspace.read_geo_data_frame(str(local_dataset_path2))
            if dataset2_geo_column:
                gdf2.set_geometry(dataset2_geo_column, inplace=True)
            validate_dataset_crs(gdf2, dataset2_georef)

            # Apply buffer if distance is provided
            # Need to project the dataset to use Web Mercator Auxiliary Sphere (EPSG:3857)
            # to make the linear units be in meters. That will allow the buffer calculation
            # to work correctly. After that the result needs to be reprojected to EPSG:4326
            # which is the assumed default for all datasets supported by these tools.
            if distance:
                gdf1.to_crs(crs=CRS.from_epsg(3857))
                gdf1["geometry"] = gdf1.geometry.buffer(distance)
                gdf1.to_crs(crs=CRS.from_epsg(4326))

            # Run the spatial join operation
            if correlation_type == CorrelationTypes.INTERSECTION:
                result_gdf = gpd.GeoDataFrame(gpd.sjoin(gdf1, gdf2, how="inner"))
            else:  # CorrelationTypes.DIFFERENCE
                joined = gpd.sjoin(gdf1, gdf2, how="left")
                result_gdf = gpd.GeoDataFrame(joined[joined["index_right"].isna()].drop(columns=["index_right"]))

            # Generate summary text describing the result
            correlation_dataset_title = f"Correlation of {item1.properties['title']} and {item2.properties['title']}"
            correlation_dataset_summary = (
                f"This dataset contains {len(result_gdf)} features resulting from a {correlation_type.value} "
                f"correlation operation between {dataset1_georef} and {dataset2_georef}. "
            )

            if distance:
                correlation_dataset_summary += f"A buffer of {distance} units was applied to the first dataset. "

            # Write the derived dataset to the local workspace cache
            correlation_dataset_reference = Georeference.new_from_timestamp(
                asset_tag=selected_asset_key1, prefix=function_name
            )

            # Create a temporary directory for the correlation dataset
            temp_dir = Path(tempfile.gettempdir())
            correlation_dataset_path = (
                temp_dir / correlation_dataset_reference.item_id / f"correlation-result.{output_format}"
            )
            correlation_dataset_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the correlation dataset
            workspace.write_geo_data_frame(str(correlation_dataset_path), result_gdf)

            # Create a new STAC item describing the result
            correlation_dataset_item = create_derived_stac_item(
                correlation_dataset_reference, correlation_dataset_title, correlation_dataset_summary, item1
            )

            # Publish the result to the workspace
            workspace.create_item(item=correlation_dataset_item, temp_assets={selected_asset_key1: correlation_dataset_path})

            # Generate text for final summary including counts and references
            text_result = (
                f"The datasets {dataset1_georef} and {dataset2_georef} have been correlated using the {correlation_type.value} operation. "
                f"The correlated result is known as {correlation_dataset_reference}. "
                f"A summary of the contents is: {correlation_dataset_summary}"
            )

            return text_result

    except Exception as e:
        logger.error("An error occurred during correlation operation")
        logger.exception(e)
        raise ValueError(f"Unable to correlate the datasets: {str(e)}")
    finally:
        # Remove the correlation dataset file
        if correlation_dataset_path and correlation_dataset_path.exists():
            correlation_dataset_path.unlink()
