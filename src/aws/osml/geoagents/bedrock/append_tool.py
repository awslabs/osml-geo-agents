#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
from typing import Any, List

from ..common import GeoDataReference, Workspace
from ..spatial import append_operation
from .common_parameters import CommonParameters
from .tool_base import ToolBase, ToolExecutionError

logger = logging.getLogger(__name__)


class AppendTool(ToolBase):
    """
    A tool that combines multiple datasets into a single result by appending them.
    It allows GenAI agents to respond to queries like:
    "Combine these datasets: stac:dataset-a, stac:dataset-b, and stac:dataset-c"
    """

    def __init__(self):
        """
        Constructor for the append tool which defines the action group and function name.
        """
        super().__init__("SpatialReasoning", "APPEND")

    def handler(self, event: dict[str, Any], context: dict[str, Any], workspace: Workspace) -> dict[str, Any]:
        """
        Implementation of the append tool handler. Takes a list of dataset georeferences,
        combines them by appending, and returns the resulting dataset.

        :param event: the Lambda input event from Bedrock
        :param context: the Lambda context object for this handler
        :param workspace: the user workspace for storing large geospatial assets
        :raises ToolExecutionError: if the tool was unable to process the event
        :return: the Lambda response structure for Bedrock
        """
        logger.debug(
            f"{__name__} Received Event: ActionGroup: {event['actionGroup']}, "
            f"Function: {event['function']} with parameters: {event.get('parameters', [])}"
        )

        try:
            # Parse parameters
            datasets_param, _ = ToolBase.get_parameter_info(event, "datasets")
            if datasets_param is None:
                raise ToolExecutionError(
                    "Missing required parameter: 'datasets'. "
                    "The parameter must be provided as a list of valid geo data reference strings."
                )

            # Parse the list of dataset references
            dataset_refs: List[GeoDataReference] = []
            try:
                # Ensure datasets_param is a list
                if not isinstance(datasets_param, list):
                    raise ToolExecutionError(
                        f"Invalid 'datasets' parameter: {datasets_param}. "
                        "The parameter must be a list of valid geo data reference strings."
                    )

                # Parse each dataset reference
                for dataset_value in datasets_param:
                    try:
                        dataset_value_str = str(dataset_value)
                        dataset_refs.append(GeoDataReference(dataset_value_str))
                    except (ValueError, TypeError) as e:
                        logger.info(f"Unable to parse dataset reference: {dataset_value}", e)
                        raise ToolExecutionError(
                            f"Unable to construct a valid geo data reference from dataset value: {dataset_value}. "
                            "Each dataset must be a valid geo data reference encoded as a string (WKT, file path, or STAC reference)."
                        )
            except Exception as e:
                logger.error("Error parsing datasets parameter: %s", str(e))
                raise ToolExecutionError(
                    f"Unable to parse 'datasets' parameter: {datasets_param}. "
                    "The parameter must be a list of valid geo data reference strings."
                )

            # Parse output format parameter (optional)
            output_format = CommonParameters.parse_string_parameter(event, "output_format", is_required=False)
            if output_format is None:
                output_format = "parquet"  # Default value

            # Validate output format
            if output_format not in ["parquet", "geojson"]:
                raise ToolExecutionError(f"Invalid output_format: {output_format}. Must be one of: 'parquet', 'geojson'.")

            # Call the operation function
            text_result = append_operation(
                dataset_references=dataset_refs,
                workspace=workspace,
                function_name=self.function_name,
                output_format=output_format,
            )

            # Create and return the response
            return self.create_action_response(event, text_result, is_error=False)

        except ToolExecutionError as txe:
            # ToolExecutionErrors contain informative messages that can be relayed back to the
            # orchestration agent to help the user understand what went wrong
            raise txe
        except ValueError as ve:
            logger.error("Value error during append operation: %s", str(ve))
            raise ToolExecutionError(f"Unable to append the datasets: {str(ve)}")
        except Exception as e:
            logger.error("An unexpected exception occurred during append operation")
            logger.exception(e)
            raise ToolExecutionError(f"Unable to append the datasets: {str(e)}")
