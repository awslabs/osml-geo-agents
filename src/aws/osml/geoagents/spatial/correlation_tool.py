#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
from enum import Enum
from pathlib import Path
from typing import Any

import geopandas as gpd
from pyproj import CRS

from ..common import CommonParameters, Georeference, LocalAssets, ToolBase, ToolExecutionError, Workspace
from .spatial_utils import create_derived_stac_item, read_geo_data_frame, validate_dataset_crs, write_geo_data_frame

logger = logging.getLogger(__name__)


class CorrelationTypes(Enum):
    """Enumeration of supported correlation types."""

    INTERSECTION = "intersection"
    DIFFERENCE = "difference"


class CorrelationTool(ToolBase):
    """
    A tool capable of correlating two spatial datasets using a spatial join.
    It allows GenAI agents to respond to queries like:
    "What features from dataset georef:dataset-a intersect with features from georef:dataset-b using a 100m buffer?"
    """

    def __init__(self):
        """
        Constructor for the spatial tool which defines the action group and function name that will be
        routed to this handler.
        """
        super().__init__("SpatialReasoning", "CORRELATE")

    def handler(self, event: dict[str, Any], context: dict[str, Any], workspace: Workspace) -> dict[str, Any]:
        """
        This is the implementation of the geospatial correlation event handler. It takes two geospatial references,
        a numeric distance, and an optional correlation type as parameters, loads the datasets for the references, and then
        returns a result that is a dataset with features resulting from the spatial join operation.

        :param event: the Lambda input event from Bedrock
        :param context: the Lambda context object for this handler
        :param workspace: the user workspace for storing large geospatial assets
        :raises ToolExecutionError: the tool was unable to process the event
        :return: the Lambda response structure for Bedrock
        """

        logger.debug(
            f"{__name__} Received Event: ActionGroup: {event['actionGroup']}, "
            f"Function: {event['function']} with parameters: {event.get('parameters', [])}"
        )

        correlation_dataset_path = None
        try:
            # Parse and validate the parameters
            dataset1_georef = CommonParameters.parse_dataset_georef(event, "dataset1", is_required=True)
            dataset2_georef = CommonParameters.parse_dataset_georef(event, "dataset2", is_required=True)
            dataset1_geo_column = CommonParameters.parse_string_parameter(
                event, "dataset1_geo_column_name", is_required=False
            )
            dataset2_geo_column = CommonParameters.parse_string_parameter(
                event, "dataset2_geo_column_name", is_required=False
            )
            distance = CommonParameters.parse_distance(event, "distance")
            correlation_type = CommonParameters.parse_enum_parameter(
                event, CorrelationTypes, "correlation_type", is_required=False
            )
            correlation_type = correlation_type if correlation_type else CorrelationTypes.INTERSECTION

            # Use workspace to access the geospatial datasets
            with LocalAssets(dataset1_georef, workspace) as (item1, local_assets1), LocalAssets(
                dataset2_georef, workspace
            ) as (item2, local_assets2):

                # Select the assets to process and load them into memory
                selected_asset_key1 = next(iter(local_assets1))
                local_dataset_path1 = local_assets1[selected_asset_key1]
                gdf1 = read_geo_data_frame(local_dataset_path1)
                if dataset1_geo_column:
                    gdf1.set_geometry(dataset1_geo_column, inplace=True)
                validate_dataset_crs(gdf1, dataset1_georef)

                selected_asset_key2 = next(iter(local_assets2))
                local_dataset_path2 = local_assets2[selected_asset_key2]
                gdf2 = read_geo_data_frame(local_dataset_path2)
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
                asset_tag=selected_asset_key1, prefix=self.function_name
            )
            correlation_dataset_path = Path(
                workspace.session_local_path,
                correlation_dataset_reference.item_id,
                f"correlation-{local_dataset_path1.name}",
            )
            write_geo_data_frame(correlation_dataset_path, result_gdf)

            # Create a new STAC item describing the result
            correlation_dataset_item = create_derived_stac_item(
                correlation_dataset_reference, correlation_dataset_title, correlation_dataset_summary, item1
            )

            # Publish the result to the workspace
            workspace.publish_item(
                item=correlation_dataset_item, local_assets={selected_asset_key1: correlation_dataset_path}
            )

            # Generate text for final summary including counts and references
            text_result = (
                f"The datasets {dataset1_georef} and {dataset2_georef} have been correlated using the {correlation_type.value} operation. "
                f"The correlated result is known as {correlation_dataset_reference}. "
                f"A summary of the contents is: {correlation_dataset_summary}"
            )
            return self.create_action_response(event, text_result, is_error=False)
        except ToolExecutionError as txe:
            # ToolExecutionErrors contain informative messages that can be relayed back to the
            # orchestration agent to help the user understand what went wrong.
            raise txe
        except Exception as e:
            logger.error("A generic / unexpected exception has been thrown by the correlation processing")
            logger.exception(e)
            raise ToolExecutionError("Unable to correlate the datasets.") from e
        finally:
            # Remove the correlation dataset file
            if correlation_dataset_path and correlation_dataset_path.exists():
                correlation_dataset_path.unlink()
