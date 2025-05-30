#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
from pyproj import CRS
from sklearn.cluster import DBSCAN

from ..common import CommonParameters, Georeference, LocalAssets, ToolBase, ToolExecutionError, Workspace
from .spatial_utils import create_derived_stac_item, read_geo_data_frame, validate_dataset_crs, write_geo_data_frame

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

        cluster_dataset_paths = []
        try:
            # Parse and validate the required parameters
            dataset_georef = CommonParameters.parse_dataset_georef(event, is_required=True)
            distance_meters = CommonParameters.parse_distance(event, "distance", is_required=True)
            max_clusters = CommonParameters.parse_numeric_parameter(event, "max_clusters", is_required=False)

            # Use context manager to handle local assets
            with LocalAssets(dataset_georef, workspace) as (item, local_asset_paths):
                # Select the assets to process and load them into memory
                selected_asset_key = next(iter(local_asset_paths))
                local_dataset_path = local_asset_paths[selected_asset_key]
                gdf = read_geo_data_frame(local_dataset_path)
                validate_dataset_crs(gdf, dataset_georef)

                # Project to Web Mercator (EPSG:3857) for meter-based calculations
                gdf = gdf.to_crs(crs=CRS.from_epsg(3857))

                # Extract center points for clustering
                centers = gpd.GeoDataFrame(geometry=gdf.geometry.centroid, crs=gdf.crs)

                # Run DBSCAN clustering
                clustering = DBSCAN(eps=distance_meters, min_samples=2).fit(
                    centers.geometry.apply(lambda p: [p.x, p.y]).tolist()
                )
                gdf["cluster"] = clustering.labels_

                # Project back to EPSG:4326
                gdf = gdf.to_crs(crs=CRS.from_epsg(4326))

                # Group features by cluster (excluding noise points labeled as -1)
                clusters = []
                for cluster_id, cluster_gdf in gdf[gdf["cluster"] != -1].groupby("cluster"):
                    clusters.append((cluster_id, len(cluster_gdf), cluster_gdf))

                # Sort clusters by size (number of features) in descending order
                clusters.sort(key=lambda x: x[1], reverse=True)

                # Limit to max_clusters if specified
                if max_clusters:
                    clusters = clusters[: int(max_clusters)]

                # Create a single base georeference for all clusters
                base_georef = Georeference.new_random()

                # Prepare assets dictionary and cluster information
                assets = {}
                cluster_info = []

                # Process each cluster
                for cluster_id, cluster_size, cluster_gdf in clusters:
                    # Create unique asset key for this cluster
                    asset_key = f"cluster-{cluster_id}"

                    # Create path for cluster dataset
                    cluster_dataset_path = Path(
                        workspace.session_local_path,
                        base_georef.item_id,
                        f"{asset_key}-{local_dataset_path.name}",
                    )
                    cluster_dataset_paths.append(cluster_dataset_path)

                    # Write cluster data
                    write_geo_data_frame(cluster_dataset_path, cluster_gdf)

                    # Add to assets dictionary
                    assets[asset_key] = cluster_dataset_path

                    # Store cluster info for summary
                    cluster_info.append((asset_key, cluster_size))

                # Generate summary text
                total_clusters = len(gdf[gdf["cluster"] != -1]["cluster"].unique())
                saved_clusters = len(cluster_info)

                dataset_title = f"Clusters from {item.properties['title']}"
                dataset_summary = (
                    f"This dataset contains {saved_clusters} clusters extracted from {dataset_georef} "
                    f"using DBSCAN clustering with a distance threshold of {distance_meters} meters. "
                )

                if max_clusters and total_clusters > max_clusters:
                    dataset_summary += f"Only the {saved_clusters} largest clusters were kept as requested. "

                dataset_summary += "\nCluster sizes:\n"
                for asset_key, size in cluster_info:
                    dataset_summary += f"- {asset_key}: {size} features\n"

                # Create STAC item for all clusters
                clusters_item = create_derived_stac_item(base_georef, dataset_title, dataset_summary, item)

                # Publish single item with all cluster assets
                workspace.publish_item(item=clusters_item, local_assets=assets)

                # Generate text result
                text_result = (
                    f"Found {total_clusters} clusters in dataset {dataset_georef} using a "
                    f"distance threshold of {distance_meters} meters. "
                )

                if max_clusters and total_clusters > max_clusters:
                    text_result += f"Saved the {saved_clusters} largest clusters as requested. "

                text_result += f"\nAll clusters are available in {base_georef} with the following assets:\n"
                for asset_key, size in cluster_info:
                    text_result += f"- {asset_key}: {size} features\n"

                return self.create_action_response(event, text_result, is_error=False)

        except ToolExecutionError as txe:
            # ToolExecutionErrors contain informative messages that can be relayed back to the
            # orchestration agent to help the user understand what went wrong.
            raise txe
        except Exception as e:
            logger.error("A generic / unexpected exception has been thrown by the cluster processing")
            logger.exception(e)
            raise ToolExecutionError("Unable to cluster the dataset.") from e
        finally:
            # Remove the cluster dataset files
            for path in cluster_dataset_paths:
                if path and path.exists():
                    path.unlink()
