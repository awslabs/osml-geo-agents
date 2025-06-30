#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
import os
from pathlib import Path
from typing import Optional

from fsspec.implementations.local import LocalFileSystem
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from shapely import from_wkt

from ..common import Georeference, Workspace
from ..spatial.buffer_operation import buffer_operation
from ..spatial.cluster_operation import cluster_operation
from ..spatial.combine_operation import combine_operation
from ..spatial.correlation_operation import CorrelationTypes, correlation_operation
from ..spatial.filter_operation import filter_operation
from ..spatial.sample_operation import sample_operation
from ..spatial.summarize_operation import summarize_operation
from ..spatial.translate_operation import translate_operation

# Set up logging
logger = logging.getLogger(__name__)

# Create an MCP server
mcp = FastMCP("OversightML GeoAgents MCP Server", port=8000, host="127.0.0.1")

# Create a workspace for storing assets
workspace_local_cache = os.environ.get("WORKSPACE_LOCAL_CACHE", "/tmp/osml-geo-agents/cache")
workspace_path = Path(workspace_local_cache)
workspace_path.mkdir(parents=True, exist_ok=True)
workspace = Workspace(filesystem=LocalFileSystem(), prefix=workspace_local_cache)


@mcp.tool()
def buffer_geometry(
    geometry: str = Field(description="WKT string representation of the geometry to buffer"),
    distance: float = Field(description="Buffer distance in meters (must be positive)"),
) -> str:
    """
    Buffer a geometry by a specified distance in meters.
    """
    logger.info(f"Buffering geometry with distance {distance}m")

    try:
        # Convert WKT string to Shapely geometry
        shapely_geometry = from_wkt(geometry)

        # Call the buffer operation
        result = buffer_operation(shapely_geometry, distance)

        return result
    except Exception as e:
        logger.error(f"Error in buffer_geometry: {e}")
        return f"Error buffering geometry: {str(e)}"


@mcp.tool()
def cluster_features(
    dataset: str = Field(description="Georeference string for the dataset"),
    distance: float = Field(description="Distance threshold in meters for clustering"),
    max_clusters: Optional[int] = Field(
        description="Optional maximum number of clusters to return (largest first)", default=None
    ),
    output_format: str = Field(description="Format for the output file (geojson or parquet)", default="parquet"),
) -> str:
    """
    Cluster features in a dataset using DBSCAN based on their geometric centers.
    """
    logger.info(f"Clustering features in {dataset} with distance {distance}m")

    try:
        # Parse the dataset georeference
        dataset_georef = Georeference(dataset)

        # Call the cluster operation
        result = cluster_operation(dataset_georef, distance, max_clusters, workspace, "cluster_features", output_format)

        return result
    except Exception as e:
        logger.error(f"Error in cluster_features: {e}")
        return f"Error clustering features: {str(e)}"


@mcp.tool()
def correlate_datasets(
    dataset1: str = Field(description="Georeference string for the first dataset"),
    dataset2: str = Field(description="Georeference string for the second dataset"),
    correlation_type: str = Field(
        description='Type of correlation to perform ("intersection" or "difference")', default="intersection"
    ),
    distance: Optional[float] = Field(
        description="Optional buffer distance in meters to apply to the first dataset", default=None
    ),
    dataset1_geo_column: Optional[str] = Field(
        description="Optional name of the geometry column in the first dataset", default=None
    ),
    dataset2_geo_column: Optional[str] = Field(
        description="Optional name of the geometry column in the second dataset", default=None
    ),
    output_format: str = Field(description="Format for the output file (geojson or parquet)", default="parquet"),
) -> str:
    """
    Correlate two spatial datasets using a spatial join.
    """
    logger.info(f"Correlating datasets {dataset1} and {dataset2}")

    try:
        # Parse the dataset georeferences
        dataset1_georef = Georeference(dataset1)
        dataset2_georef = Georeference(dataset2)

        # Convert correlation_type string to enum
        corr_type = (
            CorrelationTypes.INTERSECTION if correlation_type.lower() == "intersection" else CorrelationTypes.DIFFERENCE
        )

        # Call the correlation operation
        result = correlation_operation(
            dataset1_georef,
            dataset2_georef,
            corr_type,
            distance,
            dataset1_geo_column,
            dataset2_geo_column,
            workspace,
            "correlate_datasets",
            output_format,
        )

        return result
    except Exception as e:
        logger.error(f"Error in correlate_datasets: {e}")
        return f"Error correlating datasets: {str(e)}"


@mcp.tool()
def filter_dataset(
    dataset: str = Field(description="Georeference string for the dataset to filter"),
    filter: str = Field(description="WKT string representation of the geometry to use as a filter"),
    output_format: str = Field(description="Format for the output file (geojson or parquet)", default="parquet"),
) -> str:
    """
    Filter a dataset to only contain features that intersect a given geometry.
    """
    logger.info(f"Filtering dataset {dataset}")

    try:
        # Parse the dataset georeference
        dataset_georef = Georeference(dataset)

        # Convert filter WKT string to Shapely geometry
        filter_geometry = from_wkt(filter)

        # Call the filter operation
        result = filter_operation(dataset_georef, filter_geometry, workspace, "filter_dataset", output_format)

        return result
    except Exception as e:
        logger.error(f"Error in filter_dataset: {e}")
        return f"Error filtering dataset: {str(e)}"


@mcp.tool()
def sample_features(
    dataset: str = Field(description="Georeference string for the dataset to sample"),
    number_of_features: int = Field(description="Number of features to sample", default=10),
) -> str:
    """
    Return a text representation of features from a geodataset.
    """
    logger.info(f"Sampling {number_of_features} features from {dataset}")

    try:
        # Parse the dataset georeference
        dataset_georef = Georeference(dataset)

        # Call the sample operation
        result = sample_operation(dataset_georef, number_of_features, workspace)

        return result
    except Exception as e:
        logger.error(f"Error in sample_features: {e}")
        return f"Error sampling features: {str(e)}"


@mcp.tool()
def summarize_dataset(dataset: str = Field(description="Georeference string for the dataset to summarize")) -> str:
    """
    Generate a natural language description of columns in a geodataset.
    """
    logger.info(f"Summarizing dataset {dataset}")

    try:
        # Parse the dataset georeference
        dataset_georef = Georeference(dataset)

        # Call the summarize operation
        result = summarize_operation(dataset_georef, workspace)

        return result
    except Exception as e:
        logger.error(f"Error in summarize_dataset: {e}")
        return f"Error summarizing dataset: {str(e)}"


@mcp.tool()
def translate_geometry(
    geometry: str = Field(description="WKT string representation of the geometry to translate"),
    distance: float = Field(description="Distance to translate in meters"),
    heading: float = Field(description="Heading in degrees (0 = North, 90 = East, etc.)"),
) -> str:
    """
    Translate a geometry by a specified distance and heading.
    """
    logger.info(f"Translating geometry {distance}m at heading {heading}°")

    try:
        # Convert WKT string to Shapely geometry
        shapely_geometry = from_wkt(geometry)

        # Call the translate operation
        result = translate_operation(shapely_geometry, distance, heading)

        return result
    except Exception as e:
        logger.error(f"Error in translate_geometry: {e}")
        return f"Error translating geometry: {str(e)}"


@mcp.tool()
def combine_geometries(
    geometry1: str = Field(description="WKT string representation of the first geometry"),
    geometry2: str = Field(description="WKT string representation of the second geometry"),
    operation: str = Field(description='Type of operation to perform ("union", "intersection", or "difference")'),
) -> str:
    """
    Combine two geometries using the specified operation (union, intersection, or difference).
    """
    logger.info(f"Combining geometries using {operation} operation")

    try:
        # Convert WKT strings to Shapely geometries
        shapely_geometry1 = from_wkt(geometry1)
        shapely_geometry2 = from_wkt(geometry2)

        # Call the combine operation
        result = combine_operation(shapely_geometry1, shapely_geometry2, operation)

        return result
    except Exception as e:
        logger.error(f"Error in combine_geometries: {e}")
        return f"Error combining geometries: {str(e)}"


def configure_logging(level: int = logging.DEBUG) -> None:
    """
    Configure logging for the MCP server.

    :param level: The logging level to use
    """
    logging.basicConfig(level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger.info(f"Logging configured with level {level}")


if __name__ == "__main__":
    # Configure logging
    configure_logging()

    # Run the server
    logger.info("Starting OSML GeoAgents MCP Server")
    logger.info(f" Workspace Local Directory: {workspace_local_cache}")

    # Note Cline seems to have a bug that prevents it from communicating with
    # streamable-http MCP servers. Falling back to the deprecated sse baseline
    # until that is fixed.
    # https://github.com/cline/cline/issues/3315
    mcp.run(
        transport="sse"
        # transport="streamable-http"
    )

    logger.info("Finished OSML GeoAgents MCP Server")
