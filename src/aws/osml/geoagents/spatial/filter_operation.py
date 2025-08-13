#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import ast
import logging
import re
import tempfile
from enum import Enum
from pathlib import Path
from typing import List, Optional, Set, Tuple

import geopandas as gpd
import pandas as pd

from ..common import GeoDataReference, LocalAssets, STACReference, Workspace
from .spatial_utils import create_derived_stac_item, load_geo_data_frame

logger = logging.getLogger(__name__)


class FilterTypes(Enum):
    """Enumeration of supported filter types."""

    INTERSECTS = "intersects"
    DIFFERENCE = "difference"


def _validate_query_expression(query_expression: str, dataframe: pd.DataFrame) -> str:
    """
    Validate a query expression to ensure it only references existing columns and uses allowed operations.

    :param query_expression: The query expression to validate
    :param dataframe: The dataframe to validate against
    :return: The validated query expression
    :raises ValueError: If the query expression is invalid
    """
    if not query_expression or not query_expression.strip():
        raise ValueError("Query expression cannot be empty")

    # Get the list of column names in the dataframe
    available_columns = set(dataframe.columns)

    # Parse the expression into an AST
    try:
        parsed_expr = ast.parse(query_expression, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"Invalid query syntax: {str(e)}")

    # Extract column references and validate operations
    referenced_columns, invalid_operations = _extract_references_and_validate(parsed_expr.body, available_columns)

    # Check if all referenced columns exist in the dataframe
    missing_columns = referenced_columns - available_columns
    if missing_columns:
        raise ValueError(f"Query references non-existent columns: {', '.join(missing_columns)}")

    # Check if there are any invalid operations
    if invalid_operations:
        raise ValueError(f"Query contains disallowed operations: {', '.join(invalid_operations)}")

    return query_expression


def _extract_references_and_validate(node: ast.AST, available_columns: Set[str]) -> Tuple[Set[str], List[str]]:
    """
    Extract column references from an AST node and validate operations.

    :param node: The AST node to process
    :param available_columns: Set of available column names
    :return: Tuple of (referenced_columns, invalid_operations)
    """
    referenced_columns = set()
    invalid_operations = []

    # Allowed binary operators
    allowed_bin_ops = (
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.FloorDiv,
        ast.Mod,
        ast.Pow,
        ast.LShift,
        ast.RShift,
        ast.BitOr,
        ast.BitXor,
        ast.BitAnd,
        ast.MatMult,
    )

    # Allowed comparison operators
    allowed_cmp_ops = (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Is, ast.IsNot, ast.In, ast.NotIn)

    # Allowed boolean operators
    allowed_bool_ops = (ast.And, ast.Or)

    # Allowed unary operators
    allowed_unary_ops = (ast.UAdd, ast.USub, ast.Not, ast.Invert)

    # Process different node types
    if isinstance(node, ast.Name):
        # Simple column reference
        referenced_columns.add(node.id)

    elif isinstance(node, ast.Attribute):
        # Handle attribute access (e.g., column.str.contains())
        if isinstance(node.value, ast.Attribute) and isinstance(node.value.value, ast.Name):
            if node.value.attr == "str":
                # String method access (e.g., column.str.contains)
                column_name = node.value.value.id
                referenced_columns.add(column_name)

                # Validate string methods
                allowed_str_methods = {"contains", "startswith", "endswith", "match", "len"}
                if node.attr not in allowed_str_methods:
                    invalid_operations.append(f"String method '{node.attr}' is not allowed")
            else:
                # Other attribute access
                invalid_operations.append(f"Attribute access '{node.value.attr}.{node.attr}' is not allowed")
        elif isinstance(node.value, ast.Name):
            # Simple attribute access (e.g., column.attribute)
            referenced_columns.add(node.value.id)
            if node.attr not in {"str"}:
                invalid_operations.append(f"Attribute '{node.attr}' is not allowed")

    elif isinstance(node, ast.Call):
        # Function call
        if isinstance(node.func, ast.Attribute):
            # Method call (e.g., column.str.contains('text'))
            if isinstance(node.func.value, ast.Attribute) and isinstance(node.func.value.value, ast.Name):
                if node.func.value.attr == "str":
                    # String method call
                    column_name = node.func.value.value.id
                    referenced_columns.add(column_name)

                    # First check if the string method is allowed
                    allowed_str_methods = {"contains", "startswith", "endswith", "match", "len"}
                    if node.func.attr not in allowed_str_methods:
                        invalid_operations.append(f"String method '{node.func.attr}' is not allowed")

                    # Validate string method arguments for allowed methods
                    elif node.func.attr in {"contains", "startswith", "endswith", "match"}:
                        # These methods should have a string literal as first argument
                        if (
                            not node.args
                            or not isinstance(node.args[0], ast.Constant)
                            or not isinstance(node.args[0].value, str)
                        ):
                            invalid_operations.append(
                                f"String method '{node.func.attr}' must have a string literal as argument"
                            )

                        # For match method, validate regex pattern
                        if node.func.attr == "match" and len(node.args) > 0 and isinstance(node.args[0], ast.Constant):
                            pattern = node.args[0].value
                            if isinstance(pattern, str):
                                try:
                                    # Check if regex is valid and not too complex
                                    if len(pattern) > 100:  # Limit pattern length
                                        invalid_operations.append("Regex pattern is too complex")
                                    re.compile(pattern)
                                except re.error:
                                    invalid_operations.append("Invalid regex pattern")
                            else:
                                invalid_operations.append("Regex pattern must be a string")

                    # Process keyword arguments
                    for keyword in node.keywords:
                        if not isinstance(keyword.value, (ast.Constant, ast.NameConstant)):
                            invalid_operations.append(f"Keyword argument '{keyword.arg}' must be a literal value")
                else:
                    invalid_operations.append(f"Method call '{node.func.value.attr}.{node.func.attr}' is not allowed")
            else:
                invalid_operations.append(f"Function call '{ast.unparse(node.func)}' is not allowed")
        else:
            invalid_operations.append(f"Function call '{ast.unparse(node.func)}' is not allowed")

        # Recursively process arguments
        for arg in node.args:
            sub_refs, sub_invalids = _extract_references_and_validate(arg, available_columns)
            referenced_columns.update(sub_refs)
            invalid_operations.extend(sub_invalids)

        for keyword in node.keywords:
            sub_refs, sub_invalids = _extract_references_and_validate(keyword.value, available_columns)
            referenced_columns.update(sub_refs)
            invalid_operations.extend(sub_invalids)

    elif isinstance(node, ast.BinOp):
        # Binary operation
        if not isinstance(node.op, allowed_bin_ops):
            invalid_operations.append(f"Binary operator '{type(node.op).__name__}' is not allowed")

        left_refs, left_invalids = _extract_references_and_validate(node.left, available_columns)
        right_refs, right_invalids = _extract_references_and_validate(node.right, available_columns)

        referenced_columns.update(left_refs)
        referenced_columns.update(right_refs)
        invalid_operations.extend(left_invalids)
        invalid_operations.extend(right_invalids)

    elif isinstance(node, ast.Compare):
        # Comparison operation
        for op in node.ops:
            if not isinstance(op, allowed_cmp_ops):
                invalid_operations.append(f"Comparison operator '{type(op).__name__}' is not allowed")

        left_refs, left_invalids = _extract_references_and_validate(node.left, available_columns)
        referenced_columns.update(left_refs)
        invalid_operations.extend(left_invalids)

        for comparator in node.comparators:
            comp_refs, comp_invalids = _extract_references_and_validate(comparator, available_columns)
            referenced_columns.update(comp_refs)
            invalid_operations.extend(comp_invalids)

    elif isinstance(node, ast.BoolOp):
        # Boolean operation
        if not isinstance(node.op, allowed_bool_ops):
            invalid_operations.append(f"Boolean operator '{type(node.op).__name__}' is not allowed")

        for value in node.values:
            val_refs, val_invalids = _extract_references_and_validate(value, available_columns)
            referenced_columns.update(val_refs)
            invalid_operations.extend(val_invalids)

    elif isinstance(node, ast.UnaryOp):
        # Unary operation
        if not isinstance(node.op, allowed_unary_ops):
            invalid_operations.append(f"Unary operator '{type(node.op).__name__}' is not allowed")

        operand_refs, operand_invalids = _extract_references_and_validate(node.operand, available_columns)
        referenced_columns.update(operand_refs)
        invalid_operations.extend(operand_invalids)

    elif isinstance(node, ast.Constant):
        # Literal values are allowed
        pass
    elif isinstance(node, (ast.Num, ast.Str, ast.NameConstant)):
        # These are deprecated in Python 3.14 but still need to be handled for backward compatibility
        # Literal values are allowed
        pass

    else:
        # Any other node type is not allowed
        invalid_operations.append(f"Operation '{type(node).__name__}' is not allowed")

    return referenced_columns, invalid_operations


def filter_operation(
    function_name: str,
    workspace: Workspace,
    dataset_reference: GeoDataReference,
    filter_reference: Optional[GeoDataReference] = None,
    filter_type: Optional[FilterTypes] = None,
    dataset_geo_column: Optional[str] = None,
    filter_geo_column: Optional[str] = None,
    output_format: str = "parquet",
    query_expression: Optional[str] = None,
) -> str:
    """
    Filter a dataset to only contain features based on their spatial relationship with another dataset
    and/or a query expression for non-spatial columns.

    :param dataset_reference: GeoDataReference for the dataset to filter
    :param filter_reference: Optional GeoDataReference for the dataset to use as a spatial filter
    :param filter_type: Type of filter to apply (intersects or difference)
    :param workspace: Workspace for storing assets
    :param function_name: Function name for creating reference
    :param dataset_geo_column: Optional name of the geometry column in the dataset
    :param filter_geo_column: Optional name of the geometry column in the filter dataset
    :param output_format: Format for the output file (geojson or parquet)
    :param query_expression: Optional pandas query expression to filter non-spatial columns
                            (e.g. 'population > 1000 and city == "New York"')
    :return: A formatted string with the filtering result
    :raises ValueError: If filtering fails
    """
    filtered_dataset_path = None

    try:
        # Use workspace to access the dataset
        with LocalAssets(dataset_reference, workspace) as (item, local_asset_paths):
            # Load the dataset using the utility function
            gdf, item, selected_asset_key = load_geo_data_frame(
                local_asset_paths, workspace, dataset_reference, item, dataset_geo_column
            )

            # Store original count for summary
            original_count = len(gdf)

            # Apply query expression if provided
            if query_expression:
                try:
                    # Validate the query expression before applying it
                    validated_query = _validate_query_expression(query_expression, gdf)
                    gdf = gdf.query(validated_query)
                    logger.info(
                        f"Applied query expression '{query_expression}', filtered from {original_count} to {len(gdf)} features"
                    )
                except ValueError as e:
                    logger.error(f"Invalid query expression: {str(e)}")
                    raise ValueError(f"Invalid query expression: {str(e)}")
                except Exception as e:
                    logger.error(f"Error applying query expression: {str(e)}")
                    raise ValueError(f"Error applying query expression: {str(e)}")

            # Apply spatial filter if provided
            if filter_reference:
                # Default to INTERSECTS if filter_type is not provided
                filter_type = filter_type if filter_type else FilterTypes.INTERSECTS

                # Access the filter dataset
                with LocalAssets(filter_reference, workspace) as (filter_item, filter_local_asset_paths):
                    # Load the filter dataset using the utility function
                    filter_gdf, filter_item, filter_asset_key = load_geo_data_frame(
                        filter_local_asset_paths, workspace, filter_reference, filter_item, filter_geo_column
                    )

                    # Run the spatial filter operation
                    if filter_type == FilterTypes.INTERSECTS:
                        # Perform spatial join to find features that intersect
                        joined = gpd.sjoin(gdf, filter_gdf, how="inner")
                        filtered_gdf = gpd.GeoDataFrame(joined.drop(columns=["index_right"]))
                    else:  # FilterTypes.DIFFERENCE
                        # Perform spatial join to find features that don't intersect
                        joined = gpd.sjoin(gdf, filter_gdf, how="left")
                        filtered_gdf = gpd.GeoDataFrame(joined[joined["index_right"].isna()].drop(columns=["index_right"]))
            else:
                # If no spatial filter, just use the dataset (possibly already filtered by query)
                filtered_gdf = gdf

            # Generate summary text describing the result
            filtered_dataset_title = f"Filtered {item.properties['title']}"
            filtered_dataset_summary = (
                f"This dataset contains {len(filtered_gdf)} features selected from {dataset_reference}. "
            )

            # Add details about the filters applied
            if filter_reference:
                filter_type_value = filter_type.value if filter_type else FilterTypes.INTERSECTS.value
                filtered_dataset_summary += f"A {filter_type_value} spatial filter against {filter_reference} was applied. "
            if query_expression:
                filtered_dataset_summary += f"A query expression '{query_expression}' was also applied. "

            # Write the derived dataset to the local workspace cache
            stac_ref = STACReference.new_from_timestamp(asset_tag=selected_asset_key, prefix=function_name)
            filtered_dataset_reference = GeoDataReference.from_stac_reference(stac_ref)

            # Create a temporary directory for the filtered dataset
            temp_dir = Path(tempfile.gettempdir())
            filtered_dataset_path = temp_dir / stac_ref.item_id / f"filtered-result.{output_format}"
            filtered_dataset_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the filtered dataset
            workspace.write_geo_data_frame(str(filtered_dataset_path), filtered_gdf)

            # Create a new STAC item describing the result
            filtered_dataset_item = create_derived_stac_item(
                filtered_dataset_reference, filtered_dataset_title, filtered_dataset_summary, item
            )

            # Publish the result to the workspace
            workspace.create_item(item=filtered_dataset_item, temp_assets={selected_asset_key: filtered_dataset_path})

            # Generate text for final summary including counts and references
            text_result = (
                f"The dataset {dataset_reference} has been filtered. "
                f"The filtered result is known as {filtered_dataset_reference}. "
                f"A summary of the contents is: {filtered_dataset_summary}"
            )

            return text_result

    except Exception as e:
        logger.error("An error occurred during filter operation")
        logger.exception(e)
        raise ValueError(f"Unable to filter the dataset: {str(e)}")
    finally:
        # Remove the filtered dataset file
        if filtered_dataset_path and filtered_dataset_path.exists():
            filtered_dataset_path.unlink()
