#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
from typing import Any

from ..common import CommonParameters, ToolBase, ToolExecutionError, Workspace
from .cluster_operation import cluster_operation

logger = logging.getLogger(__name__)


class ClusterTool(ToolBase):
    """
    A tool capable of clustering features in a dataset using DBSCAN based on their geometric centers.
    It allows GenAI agents to respond to queries like:
    "Find clusters of features in dataset georef:dataset-a using a 100m distance threshold" or
    "Find the 5 largest clusters in dataset georef:dataset-b using a 50m distance threshold"
    """

    def __init__(self):
        """
        Constructor for the spatial tool which defines the action group and function name that will be
        routed to this handler.
        """
        super().__init__("SpatialReasoning", "CLUSTER")

    def handler(self, event: dict[str, Any], context: dict[str, Any], workspace: Workspace) -> dict[str, Any]:
        """
        This is the implementation of the geospatial clustering event handler. It takes a geospatial reference
        and a distance threshold in meters as parameters, loads the dataset for the reference, and then returns
        multiple datasets containing the features in each cluster.

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
            distance_meters = CommonParameters.parse_distance(event, "distance", is_required=True)
            max_clusters = CommonParameters.parse_numeric_parameter(event, "max_clusters", is_required=False)

            # Call the operation function
            text_result = cluster_operation(
                dataset_georef=dataset_georef,
                distance_meters=distance_meters,
                max_clusters=max_clusters,
                workspace=workspace,
                function_name=self.function_name,
            )

            return self.create_action_response(event, text_result, is_error=False)

        except ToolExecutionError as txe:
            # ToolExecutionErrors contain informative messages that can be relayed back to the
            # orchestration agent to help the user understand what went wrong.
            raise txe
        except Exception as e:
            logger.error("A generic / unexpected exception has been thrown by the cluster processing")
            logger.exception(e)
            raise ToolExecutionError(f"Unable to cluster the dataset: {str(e)}")
