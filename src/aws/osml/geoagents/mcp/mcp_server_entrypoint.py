#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
import os
from pathlib import Path
from typing import Optional

from fsspec import filesystem
from fsspec.implementations.local import LocalFileSystem
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from shapely import from_wkt

from ..common import GeoDataReference, Workspace
from ..spatial.append_operation import append_operation
from ..spatial.buffer_operation import buffer_operation
from ..spatial.cluster_operation import cluster_operation
from ..spatial.combine_operation import CombineType, combine_operation
from ..spatial.correlation_operation import GeometryOperationType, correlation_operation
from ..spatial.filter_operation import FilterTypes, filter_operation
from ..spatial.sample_operation import sample_operation
from ..spatial.summarize_operation import summarize_operation
from ..spatial.translate_operation import translate_operation

# Set up logging
logger = logging.getLogger(__name__)


def _get_local_workspace(workspace_local_cache: str) -> Workspace:
    """
    Get the local workspace for storing assets.

    Returns:
        Workspace: The local workspace instance
    """
    logger.info(f"Using local workspace cache: {workspace_local_cache}")
    workspace_path = Path(workspace_local_cache)
    workspace_path.mkdir(parents=True, exist_ok=True)
    return Workspace(filesystem=LocalFileSystem(), prefix=workspace_local_cache)


def get_workspace() -> Workspace:
    """
    Get the workspace for storing assets.

    If WORKSPACE_BUCKET_NAME is set, use S3 filesystem, otherwise fall back to local cache.
    Also falls back to local filesystem on S3 failure.

    Returns:
        Workspace: The configured workspace instance
    """
    workspace_bucket_name = os.environ.get("WORKSPACE_BUCKET_NAME")
    workspace_local_cache = os.environ.get("WORKSPACE_LOCAL_CACHE", "/tmp/osml-geo-agents/cache")

    if workspace_bucket_name:
        logger.info(f"Using S3 workspace bucket: {workspace_bucket_name}")
        try:
            s3_filesystem = filesystem("s3")
            workspace = Workspace(filesystem=s3_filesystem, prefix=f"s3://{workspace_bucket_name}")
        except Exception as err:
            logger.error(f"Failed to initialize S3 filesystem. Falling back to local filesystem. Error: {err}")
            workspace = _get_local_workspace(workspace_local_cache)
    else:
        workspace = _get_local_workspace(workspace_local_cache)

    return workspace


def create_mcp_server(workspace: Workspace) -> FastMCP:
    """
    Create and configure an MCP server with the given workspace.

    Args:
        workspace: The workspace instance to use for storing assets

    Returns:
        FastMCP: The configured MCP server instance
    """
    # Create MCP server
    mcp = FastMCP("OversightML GeoAgents MCP Server")

    # Configure the streamable HTTP path to be at root
    mcp.settings.streamable_http_path = "/"

    @mcp.tool()
    def buffer_geometry(
        geometry: str = Field(description="WKT string representation of the geometry to buffer"),
        distance: float = Field(description="Buffer distance in meters (must be positive)"),
    ) -> str:
        """
        Create a new geometry by expanding an input geometry by a specified distance in meters.
        The output will be a geometry encoded as a Well Known Text (WKT) string.
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
        dataset: str = Field(
            description="Reference for the dataset (STAC reference (e.g. stac:ID#asset), WKT string, or local path)"
        ),
        distance: float = Field(description="Distance threshold in meters for clustering"),
        max_clusters: Optional[int] = Field(
            description="Optional maximum number of clusters to return (largest first)", default=None
        ),
        output_format: str = Field(description="Format for the output file (geojson or parquet)", default="parquet"),
    ) -> str:
        """
        Create a new dataset by clustering features from the input dataset. The new dataset will have multiple
        asset files. Each file will represent a cluster of features that are within the provided distance of
        other features in the cluster. The new dataset and its asset files will be stored in the user's workspace.
        The dataset references will be returned in the text result of this tool.
        """
        logger.info(f"Clustering features in {dataset} with distance {distance}m")

        try:
            # Parse the dataset reference
            dataset_ref = GeoDataReference(dataset)

            # Call the cluster operation
            result = cluster_operation(dataset_ref, distance, max_clusters, workspace, "cluster_features", output_format)

            return result
        except Exception as e:
            logger.error(f"Error in cluster_features: {e}")
            return f"Error clustering features: {str(e)}"

    @mcp.tool()
    def correlate_datasets(
        dataset1: str = Field(
            description="Reference for the first dataset (STAC reference (e.g. stac:ID#asset), WKT string, or local path)"
        ),
        dataset2: str = Field(
            description="Reference for the second dataset (STAC reference (e.g. stac:ID#asset), WKT string, or local path)"
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
        geometry_operation: str = Field(
            description='Operation to perform on geometries from matching rows ("left", "right", "collect", "union", "intersect", "difference")',
            default="left",
        ),
        output_format: str = Field(description="Format for the output file (geojson or parquet)", default="parquet"),
    ) -> str:
        """
        Create a new dataset that contains features from the first dataset that can be matched to the
        features in a second dataset. The new features will have columns taken from pairs of matching
        features. The new dataset will be stored in the user's workspace and will have a new asset that
        contains the resulting features.

        You can specify how to handle the geometries of matching features using the geometry_operation
        parameter. This allows you to keep the geometry from the first dataset (left), use the geometry
        from the second dataset (right), create a collection of both geometries (collect), or perform
        geometric operations like union, intersection, or difference.
        """
        logger.info(f"Correlating datasets {dataset1} and {dataset2}")

        try:
            # Parse the dataset references
            dataset1_ref = GeoDataReference(dataset1)
            dataset2_ref = GeoDataReference(dataset2)

            # Convert geometry_operation string to enum
            valid_geometry_operations = {op.value: op for op in GeometryOperationType}
            geo_op_lower = geometry_operation.lower()
            if geo_op_lower not in valid_geometry_operations:
                valid_ops = ", ".join([f'"{op}"' for op in valid_geometry_operations.keys()])
                return f"Error: Invalid geometry operation '{geometry_operation}'. Must be one of: {valid_ops}"

            geo_op = valid_geometry_operations[geo_op_lower]

            # Call the correlation operation
            result = correlation_operation(
                dataset1_ref,
                dataset2_ref,
                distance,
                dataset1_geo_column,
                dataset2_geo_column,
                workspace,
                "correlate_datasets",
                output_format,
                geo_op,
            )

            return result
        except Exception as e:
            logger.error(f"Error in correlate_datasets: {e}")
            return f"Error correlating datasets: {str(e)}"

    @mcp.tool()
    def filter_dataset(
        dataset: str = Field(
            description="Reference for the dataset (STAC reference (e.g. stac:ID#asset), WKT string, or local path)"
        ),
        filter: Optional[str] = Field(
            description="Reference for the geometry filter (STAC reference (e.g. stac:ID#asset), WKT string, or local path)",
            default=None,
        ),
        filter_type: str = Field(
            description='Type of geometry filter to apply ("intersects" or "difference")', default="intersects"
        ),
        dataset_geo_column: Optional[str] = Field(
            description="Optional name of the geometry column in the dataset", default=None
        ),
        filter_geo_column: Optional[str] = Field(
            description="Optional name of the geometry column in the filter dataset", default=None
        ),
        output_format: str = Field(description="Format for the output file (geojson or parquet)", default="parquet"),
        query_expression: Optional[str] = Field(
            description="Optional pandas query expression to filter non-spatial columns (e.g. 'population > 1000 and city == \"New York\"')",
            default=None,
        ),
    ) -> str:
        """
        Create a new dataset that contains features selected from the referenced dataset. The features included must
        match all of the criteria provided. The new dataset will be stored in the user's workspace and the reference
        of that dataset will be returned by this tool.

        This operation can filter features in two ways:
        1. Spatial filtering: Features that either intersect or are different from the filter dataset provided.
        2. Query filtering: Features that match a pandas query expression on non-spatial columns.

        You can use either spatial filtering, query filtering, or both together.

        Query Expression Examples:
        - Basic numeric comparison: 'population > 1000'
        - Text matching: 'city == "New York"'
        - Combined conditions: 'population > 1000 and area < 500'
        - Using operators: 'temperature > 32 and status == "active"'
        - Accessing columns with spaces: '`Area (km²)` > 100'
        """
        logger.info(f"Filtering dataset {dataset}")

        try:
            # Parse the dataset reference
            dataset_ref = GeoDataReference(dataset)

            # Parse the filter reference if provided
            filter_ref = None
            if filter:
                filter_ref = GeoDataReference(filter)

            # Convert filter_type string to enum if spatial filter is used
            filter_type_enum = None
            if filter_ref:
                filter_type_enum = FilterTypes.INTERSECTS if filter_type.lower() == "intersects" else FilterTypes.DIFFERENCE

            # Call the filter operation
            result = filter_operation(
                "filter_dataset",
                workspace,
                dataset_ref,
                filter_ref,
                filter_type_enum,
                dataset_geo_column,
                filter_geo_column,
                output_format,
                query_expression,
            )

            return result
        except Exception as e:
            logger.error(f"Error in filter_dataset: {e}")
            return f"Error filtering dataset: {str(e)}"

    @mcp.tool()
    def sample_features(
        dataset: str = Field(
            description="Reference for the dataset to sample (STAC reference (e.g. stac:ID#asset), WKT string, or local path)"
        ),
        number_of_features: int = Field(description="Number of features to sample", default=10),
    ) -> str:
        """
        Read a small number (1-20) features from the referenced dataset and return the results as a table.
        The dataset itself is unchanged.
        """
        logger.info(f"Sampling {number_of_features} features from {dataset}")

        try:
            # Parse the dataset reference
            dataset_ref = GeoDataReference(dataset)

            # Call the sample operation
            result = sample_operation(dataset_ref, number_of_features, workspace)

            return result
        except Exception as e:
            logger.error(f"Error in sample_features: {e}")
            return f"Error sampling features: {str(e)}"

    @mcp.tool()
    def summarize_dataset(
        dataset: str = Field(
            description="Reference for the dataset to summarize (STAC reference (e.g. stac:ID#asset), WKT string, or local path)"
        ),
    ) -> str:
        """
        Generate a natural language description of columns in the referenced dataset.
        The dataset itself is unchanged.
        """
        logger.info(f"Summarizing dataset {dataset}")

        try:
            # Parse the dataset reference
            dataset_ref = GeoDataReference(dataset)

            # Call the summarize operation
            result = summarize_operation(dataset_ref, workspace)

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
        Move (translate) a geometry by a specified distance and heading.
        The output will be a geometry encoded as a Well Known Text (WKT) string.
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
    def append_datasets(
        datasets: list[str] = Field(
            description="List of references for datasets to combine (STAC reference (e.g. stac:ID#asset), WKT string, or local path)"
        ),
        output_format: str = Field(description="Format for the output file (geojson or parquet)", default="parquet"),
    ) -> str:
        """
        Create a new dataset that contains all of the features from the referenced datasets. The new dataset will be stored in
        the user's workspace and the reference of that dataset will be returned by this tool.

        """
        logger.info(f"Appending datasets: {datasets}")

        try:
            # Convert each string to a GeoDataReference object
            dataset_refs = [GeoDataReference(dataset) for dataset in datasets]

            if not dataset_refs:
                return "Error: No datasets provided"

            # Call the append operation
            result = append_operation(dataset_refs, workspace, "append_datasets", output_format)

            return result
        except Exception as e:
            logger.error(f"Error in append_datasets: {e}")
            return f"Error appending datasets: {str(e)}"

    # Commented out this annotation to hide the combine geometries tool. Should be redundant if the new correlate works.
    # @mcp.tool()
    def combine_geometries(
        geometry1: str = Field(description="WKT string representation of the first geometry"),
        geometry2: str = Field(description="WKT string representation of the second geometry"),
        operation: str = Field(description='Type of operation to perform ("union", "intersection", or "difference")'),
    ) -> str:
        """
        Combine two geometries using the specified operation (union, intersection, or difference).
        The output will be a geometry encoded as a Well Known Text (WKT) string.
        """
        logger.info(f"Combining geometries using {operation} operation")

        try:
            # Convert WKT strings to Shapely geometries
            shapely_geometry1 = from_wkt(geometry1)
            shapely_geometry2 = from_wkt(geometry2)

            # Validate operation type
            valid_operations = ["union", "intersection", "difference"]
            operation_lower = operation.lower()
            if operation_lower not in valid_operations:
                return f"Error: Invalid operation '{operation}'. Must be one of: {', '.join(valid_operations)}"

            # Call the combine operation with validated operation type
            # Use type assertion to convert the validated string to CombineType
            operation_type: CombineType = operation_lower  # type: ignore
            result = combine_operation(shapely_geometry1, shapely_geometry2, operation_type)

            return result
        except Exception as e:
            logger.error(f"Error in combine_geometries: {e}")
            return f"Error combining geometries: {str(e)}"

    return mcp


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

    # Create MCP server for standalone use
    workspace = get_workspace()
    mcp = create_mcp_server(workspace)
    mcp.settings.host = "0.0.0.0"
    mcp.settings.stateless_http = True
    mcp.settings.json_response = True
    mcp.settings.streamable_http_path = "/"

    # Run the server
    logger.info("Starting GeoAgents MCP Server")

    mcp.run(transport="streamable-http")

    logger.info("Finished GeoAgents MCP Server")
