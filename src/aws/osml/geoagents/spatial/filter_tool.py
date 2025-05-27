#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
from pathlib import Path
from typing import Any

from ..common import CommonParameters, Georeference, ToolBase, ToolExecutionError, Workspace
from .spatial_utils import (
    create_derived_stac_item,
    download_georef_from_workspace,
    read_geo_data_frame,
    write_geo_data_frame,
)

logger = logging.getLogger(__name__)


class FilterTool(ToolBase):
    """
    A tool capable of filtering a dataset to only contain results that intersect a given geometry.
    It allows GenAI agents to respond to queries like the following:

    "How many features from dataset georef:dataset-a are within the bounding area: POLYGON
    ((-76.7142 14.9457, 84.7142 14.9457, 84.7142 22.945, -76.7142 22.945, -76.7142 14.9457))?"
    """

    def __init__(self):
        """
        Constructor for the spatial tool which defines the action group and function name that will be
        routed to this handler.
        """
        super().__init__("SpatialReasoning", "FILTER")

    def handler(self, event: dict[str, Any], context: dict[str, Any], workspace: Workspace) -> dict[str, Any]:
        """
        This is the implementation of the geospatial filter event handler. It takes a geospatial reference and
        a geometry encoded as WKT as parameters, loads the dataset for the reference, and then returns a result
        that is a dataset with features that intersect the geometry.

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

        local_assets = {}
        filtered_dataset_path = None
        try:
            # Parse and validate the required parameters
            dataset_georef = CommonParameters.parse_dataset_georef(event, is_required=True)
            filter_bounds = CommonParameters.parse_shape_parameter(event, param_name="filter", is_required=True)

            # Use workspace to access a geospatial dataset
            item, local_assets = download_georef_from_workspace(dataset_georef, workspace)

            # Select the assets to process and load them into memory
            # TODO: Decide what to do for STAC items that have multiple assets. Maybe we should add some
            #       logic to select an asset we know how to process (either by preferred asset keys
            #       or media type).
            selected_asset_key = next(iter(local_assets))
            local_dataset_path = local_assets[selected_asset_key]
            gdf = read_geo_data_frame(local_dataset_path)

            # Run the filter operation
            filtered_gdf = gdf[gdf.intersects(filter_bounds)]

            # Generate summary text describing the result
            filtered_dataset_title = f"Filtered {item.properties['title']}"
            filtered_dataset_summary = (
                f"This dataset contains {len(filtered_gdf)} features selected from "
                f"{dataset_georef} because they were within the boundary of "
                f"{filter_bounds}. "
            )

            # Write the derived dataset to the local workspace cache
            filtered_dataset_reference = Georeference.new_random(asset_tag=selected_asset_key)
            filtered_dataset_path = Path(
                workspace.session_local_path, filtered_dataset_reference.item_id, f"filtered-{local_dataset_path.name}"
            )
            write_geo_data_frame(filtered_dataset_path, filtered_gdf)

            # Create a new STAC item describing the result
            filtered_dataset_item = create_derived_stac_item(
                filtered_dataset_reference, filtered_dataset_title, filtered_dataset_summary, item
            )

            # Publish the result to the workspace
            workspace.publish_item(item=filtered_dataset_item, local_assets={selected_asset_key: filtered_dataset_path})

            # Generate text for final summary including counts and references
            text_result = (
                f"The dataset {dataset_georef} has been filtered. "
                f"The filtered result is known as {filtered_dataset_reference}."
                f"A summary of the contents is: {filtered_dataset_summary}"
            )
            return self.create_action_response(event, text_result, is_error=False)
        except ToolExecutionError as txe:
            # ToolExecutionErrors contain informative messages that can be relayed back to the
            # orchestration agent to help the user understand what went wrong. We can
            # reraise the exception here. It should be handled by the tool router.
            raise txe
        except Exception as e:
            logger.error("A generic / unexpected exception has been thrown by the filter processing")
            logger.exception(e)
            raise ToolExecutionError("Unable to filter the dataset.") from e

        finally:
            # Cleanup the local asset files
            if local_assets:
                for asset_path in local_assets.values():
                    if asset_path.exists():
                        asset_path.unlink()

            # Remove the filtered dataset file
            if filtered_dataset_path and filtered_dataset_path.exists():
                filtered_dataset_path.unlink()
