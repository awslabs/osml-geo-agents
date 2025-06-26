#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
import os
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pystac import Item

from ..bedrock import CommonParameters, ToolBase, ToolExecutionError
from ..common import Workspace

logger = logging.getLogger(__name__)


class LoadTool(ToolBase):
    """
    A tool for loading datasets from S3 into the workspace.

    This tool allows users to load datasets from S3 into their workspace. The tool takes an S3 asset URL
    as a required parameter and an optional dataset name. It downloads the asset from S3, creates a new
    STAC item for it, and publishes it to the workspace.
    """

    def __init__(self):
        """
        Constructor for the load tool which defines the action group and function name.
        """
        super().__init__("WorkspaceActions", "LOAD")

    def handler(self, event: dict[str, Any], context: dict[str, Any], workspace: Workspace) -> dict[str, Any]:
        """
        Handler for loading a dataset from S3 into the workspace.

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

        local_path = None
        try:
            # Parse parameters
            s3_url = CommonParameters.parse_string_parameter(event, "s3_url", is_required=True)
            dataset_name = CommonParameters.parse_string_parameter(event, "dataset_name", is_required=False)

            # Validate S3 URL
            parsed_url = urlparse(s3_url)
            if parsed_url.scheme != "s3":
                raise ToolExecutionError(f"Invalid S3 URL: {s3_url}. URL must start with 's3://'")

            bucket_name = parsed_url.netloc
            key = parsed_url.path.lstrip("/")

            # Use dataset name or extract from S3 key if not provided
            if not dataset_name:
                dataset_name = os.path.basename(key)

            # Create a temporary local path for the asset
            local_path = Path(workspace.session_local_path, "temp", os.path.basename(key))
            local_path.parent.mkdir(parents=True, exist_ok=True)

            # Download the asset from S3
            try:
                workspace.s3_client.download_file(
                    Bucket=bucket_name,
                    Key=key,
                    Filename=str(local_path.absolute()),
                    Config=workspace.s3_transfer_config,
                    Callback=lambda bytes_transferred: logger.info(
                        f"Downloading asset: {bytes_transferred} bytes transferred"
                    ),
                )
                logger.info(f"Completed downloading asset from {s3_url}")
            except Exception as e:
                logger.error(f"Failed to download asset from S3: {str(e)}")
                raise ToolExecutionError(f"Failed to download asset from S3: {str(e)}")

            # Create a new STAC item
            item_id = secrets.token_hex(8)  # Generate a random ID
            item = Item(
                id=item_id,
                geometry=None,  # This would need to be determined from the asset
                bbox=None,  # This would need to be determined from the asset
                datetime=datetime.now(),  # Use current time or extract from metadata
                properties={"title": dataset_name},
            )

            # Publish the item to the workspace
            try:
                asset_key = "data"
                georef = workspace.create_item(item=item, temp_assets={asset_key: local_path})
                result = f"Successfully loaded dataset from {s3_url} into the workspace. The dataset is now available as {georef}."
                return self.create_action_response(event, result)
            except Exception as e:
                logger.error(f"Failed to create item in workspace: {str(e)}")
                raise ToolExecutionError(f"Failed to create item in workspace: {str(e)}")

        except ToolExecutionError as txe:
            # ToolExecutionErrors contain informative messages that can be relayed back to the
            # orchestration agent to help the user understand what went wrong.
            raise txe
        except Exception as e:
            logger.error("A generic / unexpected exception has been thrown by the load processing")
            logger.exception(e)
            raise ToolExecutionError(f"Failed to load dataset: {str(e)}") from e
        finally:
            # Clean up the temporary file
            if local_path and local_path.exists():
                try:
                    local_path.unlink()
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file {local_path}: {str(e)}")
