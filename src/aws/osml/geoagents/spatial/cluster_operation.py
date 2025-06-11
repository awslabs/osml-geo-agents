#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
from pathlib import Path
from typing import Optional

import geopandas as gpd
import numpy as np
from pyproj import CRS
from sklearn.cluster import DBSCAN

from ..common import Georeference, LocalAssets, Workspace
from .spatial_utils import create_derived_stac_item, read_geo_data_frame, validate_dataset_crs, write_geo_data_frame

logger = logging.getLogger(__name__)


def cluster_operation(
    dataset_georef: Georeference,
    distance_meters: float,
    max_clusters: Optional[float],
    workspace: Workspace,
    function_name: str,
) -> str:
    """
    Cluster features in a dataset using DBSCAN based on their geometric centers.

    :param dataset_georef: Georeference for the dataset to cluster
    :param distance_meters: Distance threshold in meters for clustering
    :param max_clusters: Optional maximum number of clusters to return (largest first)
    :param workspace: Workspace for storing assets
    :param function_name: Function name for creating georeference
    :return: A formatted string with the clustering result
    :raises ValueError: If clustering fails
    """
    cluster_dataset_paths = []

    try:
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
            # Convert to numpy array to satisfy type checker
            points = np.array(centers.geometry.apply(lambda p: [p.x, p.y]).tolist())
            clustering = DBSCAN(eps=distance_meters, min_samples=2).fit(points)
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
            base_georef = Georeference.new_from_timestamp(prefix=function_name)

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

            return text_result

    except Exception as e:
        logger.error("An error occurred during clustering operation")
        logger.exception(e)
        raise ValueError(f"Unable to cluster the dataset: {str(e)}")
    finally:
        # Remove the cluster dataset files
        for path in cluster_dataset_paths:
            if path and path.exists():
                path.unlink()
