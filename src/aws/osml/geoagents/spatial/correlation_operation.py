#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
import tempfile
from enum import Enum
from pathlib import Path
from typing import Optional

import geopandas as gpd
from pyproj import CRS
from shapely.geometry import GeometryCollection

from ..common import GeoDataReference, LocalAssets, STACReference, Workspace
from .spatial_utils import create_derived_stac_item, load_geo_data_frame

logger = logging.getLogger(__name__)


class GeometryOperationType(Enum):
    """Enumeration of supported geometry operations for correlation results."""

    LEFT = "left"  # Only the geometry column from the first dataset is used in the result
    RIGHT = "right"  # Only the geometry column from the second dataset is used in the result
    COLLECT = "collect"  # All geometries are combined into a GeometryCollection
    UNION = "union"  # The resulting geometry is the union of both geometries
    INTERSECT = "intersect"  # The resulting geometry is the intersection of both geometries
    DIFFERENCE = "difference"  # The resulting geometry is the difference between geometries


def correlation_operation(
    dataset1_reference: GeoDataReference,
    dataset2_reference: GeoDataReference,
    distance: Optional[float],
    dataset1_geo_column: Optional[str],
    dataset2_geo_column: Optional[str],
    workspace: Workspace,
    function_name: str,
    output_format: str = "parquet",
    geometry_operation: GeometryOperationType = GeometryOperationType.LEFT,
) -> str:
    """
    Correlate two spatial datasets using a spatial join with intersection.

    :param dataset1_reference: GeoDataReference for the first dataset
    :param dataset2_reference: GeoDataReference for the second dataset
    :param distance: Optional buffer distance in meters to apply to the first dataset
    :param dataset1_geo_column: Optional name of the geometry column in the first dataset
    :param dataset2_geo_column: Optional name of the geometry column in the second dataset
    :param workspace: Workspace for storing assets
    :param function_name: Function name for creating reference
    :param output_format: Format for the output file (geojson or parquet)
    :param geometry_operation: Operation to perform on geometries from matching rows (left, right, collect, union, intersect, difference)
    :return: A formatted string with the correlation result
    :raises ValueError: If correlation fails
    """
    correlation_dataset_path = None

    try:
        # Use workspace to access the geospatial datasets
        with LocalAssets(dataset1_reference, workspace) as (item1, local_assets1), LocalAssets(
            dataset2_reference, workspace
        ) as (
            item2,
            local_assets2,
        ):

            # Load the first dataset using the utility function
            gdf1, item1, selected_asset_key1 = load_geo_data_frame(
                local_assets1, workspace, dataset1_reference, item1, dataset1_geo_column
            )

            # Load the second dataset using the utility function
            gdf2, item2, selected_asset_key2 = load_geo_data_frame(
                local_assets2, workspace, dataset2_reference, item2, dataset2_geo_column
            )

            # Get the actual geometry column names for both GeoDataFrames
            gdf1_geo_column = gdf1.geometry.name
            gdf2_geo_column = gdf2.geometry.name

            # Apply buffer if distance is provided
            # Need to project the dataset to use Web Mercator Auxiliary Sphere (EPSG:3857)
            # to make the linear units be in meters. That will allow the buffer calculation
            # to work correctly. After that the result needs to be reprojected to EPSG:4326
            # which is the assumed default for all datasets supported by these tools.
            if distance:
                gdf1.to_crs(crs=CRS.from_epsg(3857), inplace=True)
                gdf1[gdf1_geo_column] = gdf1[gdf1_geo_column].buffer(distance)
                gdf1.to_crs(crs=CRS.from_epsg(4326), inplace=True)

            # Copy the geometry column from gdf2 to a new column to preserve it after the join
            gdf2["matched_geometry"] = gdf2[gdf2_geo_column]

            # Perform the spatial join
            result_gdf = gpd.GeoDataFrame(gpd.sjoin(gdf1, gdf2, how="inner"))

            # Get the geometry column name for the result GeoDataFrame
            result_geo_column = result_gdf.geometry.name

            # Apply the geometry operation
            if len(result_gdf) > 0 and "matched_geometry" in result_gdf.columns:
                if geometry_operation == GeometryOperationType.RIGHT:
                    # Use the geometry from the second dataset
                    result_gdf[result_geo_column] = result_gdf["matched_geometry"]
                elif geometry_operation == GeometryOperationType.COLLECT:
                    # Create a GeometryCollection from both geometries
                    result_gdf[result_geo_column] = result_gdf.apply(
                        lambda row: GeometryCollection([row[result_geo_column], row["matched_geometry"]]), axis=1
                    )
                elif geometry_operation == GeometryOperationType.UNION:
                    # Create a union of both geometries
                    result_gdf[result_geo_column] = result_gdf.apply(
                        lambda row: row[result_geo_column].union(row["matched_geometry"]), axis=1
                    )
                elif geometry_operation == GeometryOperationType.INTERSECT:
                    # Create an intersection of both geometries
                    result_gdf[result_geo_column] = result_gdf.apply(
                        lambda row: row[result_geo_column].intersection(row["matched_geometry"]), axis=1
                    )
                elif geometry_operation == GeometryOperationType.DIFFERENCE:
                    # Create a difference between geometries
                    result_gdf[result_geo_column] = result_gdf.apply(
                        lambda row: row[result_geo_column].difference(row["matched_geometry"]), axis=1
                    )
                # For LEFT (default), keep the original geometry

                # Drop the matched_geometry column as it's no longer needed
                if "matched_geometry" in result_gdf.columns:
                    result_gdf = result_gdf.drop(columns=["matched_geometry"])

            # Generate summary text describing the result
            correlation_dataset_title = f"Correlation of {item1.properties['title']} and {item2.properties['title']}"
            correlation_dataset_summary = (
                f"This dataset contains {len(result_gdf)} features resulting from an intersection "
                f"correlation operation between {dataset1_reference} and {dataset2_reference}. "
            )

            if geometry_operation != GeometryOperationType.LEFT:
                correlation_dataset_summary += (
                    f"The '{geometry_operation.value}' geometry operation was applied to matching features. "
                )

            if distance:
                correlation_dataset_summary += f"A buffer of {distance} units was applied to the first dataset."

            # Write the derived dataset to the local workspace cache
            stac_ref = STACReference.new_from_timestamp(asset_tag=selected_asset_key1, prefix=function_name)
            correlation_dataset_reference = GeoDataReference.from_stac_reference(stac_ref)

            # Create a temporary directory for the correlation dataset
            temp_dir = Path(tempfile.gettempdir())
            correlation_dataset_path = temp_dir / stac_ref.item_id / f"correlation-result.{output_format}"
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
                f"The datasets {dataset1_reference} and {dataset2_reference} have been correlated using the intersection operation. "
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
