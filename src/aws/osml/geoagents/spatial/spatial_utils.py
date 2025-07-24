#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

import geopandas as gpd
import pandas as pd
import shapely
from pystac import Asset, Item
from shapely.geometry.base import BaseGeometry

from ..common import GeoDataReference, STACReference, Workspace

logger = logging.getLogger(__name__)


def validate_dataset_crs(dataset: gpd.GeoDataFrame, georef: GeoDataReference) -> None:
    """
    Validate and ensure a GeoDataFrame has a CRS set and is using EPSG:4326 coordinates.
    If the CRS is not set EPSG:4326 will be assumed and it will be set.

    :param dataset: GeoDataFrame to validate
    :param georef: GeoDataReference for the dataset
    :raises ValueError: if the dataset uses an unsupported CRS
    """
    if dataset.crs is None:
        dataset.set_crs("EPSG:4326", inplace=True)
    elif dataset.crs != "EPSG:4326":
        raise ValueError(f"Dataset {georef} does not use a supported CRS. Only EPSG:4326 is supported.")


def create_derived_stac_item(
    derived_dataset_reference: GeoDataReference,
    derived_dataset_title: str,
    derived_dataset_description: str,
    original_item: Item,
):
    """
    Create a new STAC Item for the result dataset. The new item will duplicate information from the original
    item when meaningful.

    :param derived_dataset_reference: the new GeoDataReference for the derived dataset
    :param derived_datset_title: the title of the derived dataset
    :param derived_dataset_description: the description of the derived dataset
    :param original_item: the original item
    :return: a new STAC item for the derived dataset
    """

    start_datetime = None
    end_datetime = None
    if "start_datetime" in original_item.properties and "end_datetime" in original_item.properties:
        start_datetime = datetime.fromisoformat(original_item.properties["start_datetime"])
        end_datetime = datetime.fromisoformat(original_item.properties["end_datetime"])

    # TODO: Consider computing better geometry and bbox attributes for this derived STAC item.
    #       In theory the new bounds should be no bigger than the filter.

    # Extract item_id from STAC reference if it's a STAC reference
    item_id = ""
    if derived_dataset_reference.is_stac_reference():
        stac_ref = STACReference(derived_dataset_reference.reference_string)
        item_id = stac_ref.item_id
    else:
        # Generate a random ID if not a STAC reference
        stac_ref = STACReference.new_from_timestamp()
        item_id = stac_ref.item_id

    filtered_dataset_item = Item(
        id=item_id,
        geometry=original_item.geometry,
        bbox=original_item.bbox,
        datetime=original_item.datetime,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        properties={
            "title": derived_dataset_title,
            "description": derived_dataset_description,
            "keywords": original_item.properties.get("keywords", []),
        },
    )
    filtered_dataset_item.add_derived_from(original_item)
    return filtered_dataset_item


def create_length_limited_wkt(shape: BaseGeometry, max_length: int = 500, minimum_precision: int = 3) -> str:
    """
    Create a WKT string representation of a shape that is shorter than the specified maximum length.

    This function progressively applies simplification and reduces coordinate precision
    until the WKT string is under the specified maximum length. This is necessary because some agent
    orchestration frameworks (e.g. Bedrock Agents) currently have limits on the length of parameters.
    We expect the WKT results from these spatial operations to be chained together. Providing a
    way to consistently limit the lengh of a result will help the orchestration engine return results
    that can easily be passed to other tools.

    :param shape: The geometry to convert to WKT
    :param max_length: Maximum length of the WKT string (default: 500 characters)
    :param minimum_precision: Minimum precision to use for coordinate rounding (default: 3)
    :return: WKT string representation under the maximum length
    :raises ValueError: If unable to create a WKT string under the maximum length
    """

    # Try different precision levels first
    for precision in range(6, minimum_precision - 1, -1):
        wkt = shapely.to_wkt(shape, rounding_precision=precision)
        if len(wkt) <= max_length:
            return wkt

    # If reducing precision isn't enough, try simplification
    # with progressively increasing tolerance. These values are in decimal degrees
    for tolerance in [0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5]:
        simplified = shape.simplify(tolerance)

        # Try different precision levels with the simplified geometry
        for precision in range(6, minimum_precision - 1, -1):
            wkt = shapely.to_wkt(simplified, rounding_precision=precision)
            if len(wkt) <= max_length:
                return wkt

    # If we still can't get under the limit, raise an error
    raise ValueError(f"Unable to create WKT string under {max_length} characters")


def load_geo_data_frame(
    local_asset_paths: Dict[str, str],
    workspace: Workspace,
    geo_reference: GeoDataReference,
    item: Optional[Item] = None,
    geo_column: Optional[str] = None,
) -> Tuple[gpd.GeoDataFrame, Item, str]:
    """
    Load a GeoDataFrame from local asset paths, handling common operations like:
    - Selecting the first asset
    - Reading the GeoDataFrame
    - Setting the geometry column if specified
    - Validating the CRS
    - Creating a STAC item if needed

    This function is designed to be used within a LocalAssets context manager.

    :param local_asset_paths: Dictionary of asset keys to local paths from LocalAssets
    :param workspace: Workspace for storing assets
    :param geo_reference: GeoDataReference for the dataset (used for validation and item creation)
    :param item: Optional existing STAC Item
    :param geo_column: Optional name of the geometry column
    :return: Tuple of (GeoDataFrame, STAC Item, selected_asset_key)
    :raises ValueError: If loading fails
    """
    # Select the assets to process and load them into memory
    selected_asset_key = next(iter(local_asset_paths))
    local_dataset_path = local_asset_paths[selected_asset_key]
    gdf = workspace.read_geo_data_frame(str(local_dataset_path))
    if geo_column:
        gdf.set_geometry(geo_column, inplace=True)
    validate_dataset_crs(gdf, geo_reference)

    # If item is None, create a new item from the GeoDataFrame
    if item is None:
        item = create_stac_item_for_dataset(
            gdf,
            str(local_dataset_path),
            title=f"Dataset from {geo_reference}",
            description=f"Dataset loaded from {geo_reference}",
        )

    return gdf, item, selected_asset_key


def create_stac_item_for_dataset(
    gdf: gpd.GeoDataFrame, path: str, title: Optional[str] = None, description: Optional[str] = None
) -> Item:
    """
    Create a STAC Item for a GeoDataFrame dataset.

    This function creates a STAC Item representing a GeoDataFrame. The Item includes:
    - A bounding box and geometry calculated from the GeoDataFrame's extent
    - Datetime properties derived from datetime columns if available, or current time if not
    - A random timestamp-based ID
    - The path to the GeoDataFrame as an asset

    :param gdf: The GeoDataFrame to create a STAC Item for
    :param path: The path to the GeoDataFrame file
    :param title: Optional title for the STAC Item
    :param description: Optional description for the STAC Item
    :return: A STAC Item representing the GeoDataFrame
    """
    # Ensure the GeoDataFrame has a valid CRS
    # Create a temporary GeoDataReference for validation
    temp_ref = GeoDataReference.from_stac_reference(STACReference.new_from_timestamp())
    validate_dataset_crs(gdf, temp_ref)

    # Generate a random timestamp-based ID
    stac_ref = STACReference.new_from_timestamp()

    # Calculate the bounding box from the GeoDataFrame
    # Convert numpy float64 values to Python floats
    bbox = [float(x) for x in gdf.total_bounds]  # [minx, miny, maxx, maxy]

    # Create a geometry that represents the bounds of the GeoDataFrame
    # Convert to GeoJSON format for STAC
    # Use union_all() instead of unary_union (which is deprecated)
    geometry = shapely.geometry.mapping(gdf.geometry.union_all().convex_hull)

    # Check if any columns are datetime type
    datetime_cols = [col for col in gdf.columns if pd.api.types.is_datetime64_any_dtype(gdf[col])]

    start_datetime = None
    end_datetime = None
    datetime_value = None

    if datetime_cols:
        # Use the first datetime column found
        datetime_col = datetime_cols[0]
        min_date = gdf[datetime_col].min()
        max_date = gdf[datetime_col].max()

        if min_date == max_date:
            datetime_value = min_date
        else:
            start_datetime = min_date
            end_datetime = max_date
            datetime_value = None  # Use None when we have a range
    else:
        # Use current time if no datetime columns are found
        datetime_value = datetime.now(timezone.utc)

    # Create the STAC Item
    item = Item(
        id=stac_ref.item_id,
        geometry=geometry,
        bbox=bbox,
        datetime=datetime_value,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        properties={
            "title": title or f"GeoDataFrame from {path}",
            "description": description or f"STAC Item created from GeoDataFrame at {path}",
        },
    )

    # Add the path as an asset
    item.add_asset(
        "data",
        Asset(
            href=path,
            media_type="application/geo+json" if path.endswith(".geojson") else "application/octet-stream",
            roles=["data"],
            title=f"GeoDataFrame data at {path}",
        ),
    )

    return item
