# Copyright 2025 Amazon.com, Inc. or its affiliates.

"""Configuration for GeoAgent integration tests."""

from dataclasses import dataclass


@dataclass
class GeoAgentIntegTestConfig:
    """
    Configuration for GeoAgent integration tests.

    Attributes:
        mcp_endpoint (str): The HTTP endpoint for the MCP server (ALB URL)
        workspace_bucket (str): The S3 bucket name for workspace storage
    """

    mcp_endpoint: str
    workspace_bucket: str
