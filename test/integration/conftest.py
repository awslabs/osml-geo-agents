# Copyright 2025 Amazon.com, Inc. or its affiliates.


import logging
import os
import re
from typing import Callable, Dict

import boto3
import pytest

from .test_mcp_client import MCPTestClient

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def mcp_client():
    """
    Create and initialize the MCP test client.

    This fixture creates an MCPTestClient directly from environment variables
    for black-box integration testing. Session scope ensures a single MCP
    connection is used for all tests.

    Returns:
        MCPTestClient: Initialized MCP test client
    """
    mcp_endpoint = os.environ.get("MCP_ENDPOINT")
    if not mcp_endpoint:
        raise ValueError("MCP_ENDPOINT environment variable is required")

    return MCPTestClient(mcp_endpoint)


@pytest.fixture(scope="session", autouse=True)
def test_datasets() -> Dict[str, str]:
    """
    Upload test datasets to S3 workspace before tests run and clean up after.

    This fixture reads real GeoJSON files from test/data directory and uploads them
    to the S3 workspace bucket. It yields a dict of dataset names to S3 paths that
    tests can use. After all tests complete, it cleans up the uploaded files.

    Returns:
        Dict mapping dataset names to S3 paths (e.g., {"recent_earthquakes": "s3://bucket/test-run-abc123/recent_earthquakes.geojson"})
    """
    import uuid

    workspace_bucket = os.environ.get("WORKSPACE_BUCKET")
    if not workspace_bucket:
        raise ValueError("WORKSPACE_BUCKET environment variable is required")

    s3_client = boto3.client("s3")
    test_run_id = str(uuid.uuid4())[:8]

    # Define test dataset files to upload (relative to Lambda task root)
    dataset_files = {
        "recent_earthquakes": "test/data/recent_earthquakes.geojson",
        "significant_earthquakes": "test/data/significant_earthquakes.geojson",
    }

    # Upload datasets and build S3 path mapping
    s3_paths = {}
    uploaded_keys = []

    for name, filepath in dataset_files.items():
        # Read the GeoJSON file
        with open(filepath, "r", encoding="utf-8") as f:
            geojson_content = f.read()

        # Define S3 key with unique test run ID to avoid conflicts
        key = f"test-datasets/{test_run_id}/integ-test-{name}.geojson"

        # Upload to S3
        s3_client.put_object(Bucket=workspace_bucket, Key=key, Body=geojson_content, ContentType="application/geo+json")

        # Store S3 path and key for cleanup
        s3_paths[name] = f"s3://{workspace_bucket}/{key}"
        uploaded_keys.append(key)

    # Yield paths for tests to use
    yield s3_paths

    # Cleanup: delete uploaded test datasets
    for key in uploaded_keys:
        try:
            s3_client.delete_object(Bucket=workspace_bucket, Key=key)
        except Exception as e:
            logger.warning(f"Failed to cleanup test dataset {key}: {e}")

    logger.info(f"Cleaned up {len(uploaded_keys)} test datasets from test run {test_run_id}")


@pytest.fixture
def stac_cleanup(request: pytest.FixtureRequest) -> Callable[[str], None]:
    """
    Track STAC reference created during a test and clean it up after the test completes.

    This function-scoped fixture uses pytest's finalizer mechanism to ensure cleanup
    happens immediately after each test, avoiding session-scope timing issues with Lambda.
    Each test creates at most one STAC item, so we only track a single reference.

    Returns:
        Function to register STAC reference from test result
    """

    workspace_bucket = os.environ.get("WORKSPACE_BUCKET")
    if not workspace_bucket:
        raise ValueError("WORKSPACE_BUCKET environment variable is required")

    s3_client = boto3.client("s3")
    stac_ref = None

    def extract_and_track_stac_ref(result_text: str) -> None:
        """
        Extract STAC reference from result text and track it for cleanup.

        STAC references follow the pattern: stac:operation_name-ID
        Example: stac:cluster_features-MIQBEXTU, stac:append_datasets-MIQBEZC7

        :param result_text: Text containing STAC reference
        """
        nonlocal stac_ref
        pattern = r"stac:([a-z_]+-[A-Z0-9]+)"
        matches = re.findall(pattern, result_text)
        if matches:
            stac_ref = matches[0]
            logger.info(f"Tracking STAC item for cleanup: {stac_ref}")

    def cleanup():
        """Cleanup function registered as finalizer - runs after test completes."""
        if stac_ref:
            try:
                prefix = f"stac/{stac_ref}/"

                paginator = s3_client.get_paginator("list_objects_v2")
                pages = paginator.paginate(Bucket=workspace_bucket, Prefix=prefix)

                objects_to_delete = []
                for page in pages:
                    if "Contents" in page:
                        objects_to_delete.extend([{"Key": obj["Key"]} for obj in page["Contents"]])

                if objects_to_delete:
                    s3_client.delete_objects(Bucket=workspace_bucket, Delete={"Objects": objects_to_delete})
                    logger.info(f"Deleted {len(objects_to_delete)} objects for STAC item {stac_ref}")
            except Exception as e:
                logger.warning(f"Failed to cleanup STAC item {stac_ref}: {e}")

    # Register cleanup to run after test completes (even on failure)
    request.addfinalizer(cleanup)

    # Return the tracking function for the test to use
    return extract_and_track_stac_ref
