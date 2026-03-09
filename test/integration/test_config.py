# Copyright 2025-2026 Amazon.com, Inc. or its affiliates.

"""Configuration for GeoAgent integration tests."""

import os
from dataclasses import dataclass

import boto3


def _resolve_mcp_endpoint() -> str:
    """Resolve the MCP server endpoint.

    If MCP_ENDPOINT is set directly, use it. Otherwise, read the SSM parameter
    name from MCP_ENDPOINT_SSM_PARAM and fetch the value at runtime.
    """
    direct = os.getenv("MCP_ENDPOINT")
    if direct:
        return direct

    ssm_param = os.getenv("MCP_ENDPOINT_SSM_PARAM")
    if ssm_param:
        try:
            ssm = boto3.client("ssm")
            resp = ssm.get_parameter(Name=ssm_param)
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve SSM parameter {ssm_param}: {e}")
        dns = resp["Parameter"]["Value"]
        return f"http://{dns}"

    raise RuntimeError("Neither MCP_ENDPOINT nor MCP_ENDPOINT_SSM_PARAM is set")


def _resolve_workspace_bucket() -> str:
    """Resolve the workspace S3 bucket name.

    If WORKSPACE_BUCKET is set directly, use it. Otherwise, read the SSM
    parameter name from WORKSPACE_BUCKET_SSM_PARAM and fetch the value at
    runtime.
    """
    direct = os.getenv("WORKSPACE_BUCKET")
    if direct:
        return direct

    ssm_param = os.getenv("WORKSPACE_BUCKET_SSM_PARAM")
    if ssm_param:
        try:
            ssm = boto3.client("ssm")
            resp = ssm.get_parameter(Name=ssm_param)
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve SSM parameter {ssm_param}: {e}")
        return resp["Parameter"]["Value"]

    raise RuntimeError("Neither WORKSPACE_BUCKET nor WORKSPACE_BUCKET_SSM_PARAM is set")


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
