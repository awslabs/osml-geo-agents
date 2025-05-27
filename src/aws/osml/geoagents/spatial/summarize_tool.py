#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
from typing import Any

from ..common import CommonParameters, ToolBase, ToolExecutionError, Workspace
from ..common.local_assets import LocalAssets
from .spatial_utils import read_geo_data_frame

logger = logging.getLogger(__name__)


class SummarizeTool(ToolBase):
    """
    A tool capable of generating natural language descriptions of columns in a geodataframe.
    It allows GenAI agents to respond to queries like:
    "What columns are available in dataset georef:dataset-a and what do they represent?"
    """

    def __init__(self):
        """
        Constructor for the spatial tool which defines the action group and function name that will be
        routed to this handler.
        """
        super().__init__("SpatialReasoning", "SUMMARIZE")

    def handler(self, event: dict[str, Any], context: dict[str, Any], workspace: Workspace) -> dict[str, Any]:
        """
        This is the implementation of the geospatial summarize event handler. It takes a geospatial reference
        as a parameter, loads the dataset, and returns a natural language description of the columns and their
        metadata.

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

        try:
            # Parse and validate the required parameters
            dataset_georef = CommonParameters.parse_dataset_georef(event, is_required=True)

            # Use context manager to handle local assets
            with LocalAssets(dataset_georef, workspace) as (item, local_asset_paths):
                # Select the assets to process and load them into memory
                selected_asset_key = next(iter(local_asset_paths))
                local_dataset_path = local_asset_paths[selected_asset_key]
                gdf = read_geo_data_frame(local_dataset_path)

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
                        # TODO: Keep this in sync with whatever implementation is chosen in the read_geo_data_frame() function.
                        #       I haven't found a solid convention that has end users create parquet files with human readable
                        #       metadata describing each column. Its possible we will need to create a new convention for that
                        #       and figure out how to augment the GeoPandas provided parsing of parquet files with that information.
                        #       Whatever approach we choose should be the same between read_geo_data_frame() and this code.
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

            return self.create_action_response(event, summary, is_error=False)

        except ToolExecutionError as txe:
            # ToolExecutionErrors contain informative messages that can be relayed back to the
            # orchestration agent to help the user understand what went wrong.
            raise txe
        except Exception as e:
            logger.error("A generic / unexpected exception has been thrown by the summarize processing")
            logger.exception(e)
            raise ToolExecutionError("Unable to summarize the dataset.") from e
