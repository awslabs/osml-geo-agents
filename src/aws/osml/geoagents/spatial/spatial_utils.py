#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import pyarrow.parquet as pq
import shapely
from pystac import Item
from shapely.geometry.base import BaseGeometry

from ..common import Georeference, ToolExecutionError

logger = logging.getLogger(__name__)


def is_parquet_file(file_path: Path) -> bool:
    """
    Check if a file is a Parquet file by reading the magic bytes at the beginning of the file.

    :param file_path: Path to the file to check
    :return: True if the file is a Parquet file, False otherwise
    """
    # Parquet files start with PAR1 magic bytes
    try:
        with open(file_path, "rb") as f:
            magic_bytes = f.read(4)
            return magic_bytes == b"PAR1"
    except Exception:
        return False


def read_field_descriptions_from_parquet(file_path: Path) -> dict[str, str]:
    """
    Read field descriptions from column metadata stored in a Parquet file.

    :param file_path: Path to the Parquet file
    :return: A dictionary of field names and their descriptions
    """
    result = {}
    schema = pq.read_table(file_path).schema
    for name in schema.names:
        field = schema.field(name)
        if field.metadata and b"comment" in field.metadata:
            result[name] = field.metadata[b"comment"].decode("utf-8")
    return result


def read_geo_data_frame(file_path: Path) -> gpd.GeoDataFrame:
    """
    Read a GeoDataFrame from a file.

    :param file_path: Path to the file to read
    :raises ToolExecutionError: if the file can not be read
    :return: the GeoDataFrame
    """
    # TODO: Dig into this and understand how GeoPandas normally handles multiple file formats.
    #       Attempting to open a parquet file with .from_file results in a PROJ error.
    #       It is unclear if that error is a problem in the dependencies/docker build or
    #       if we need this level of checking to decide how to open different file formats.
    try:
        if is_parquet_file(file_path):
            gdf = gpd.read_parquet(file_path)
            gdf.attrs["column-descriptions"] = read_field_descriptions_from_parquet(file_path)
        else:
            gdf = gpd.GeoDataFrame.from_file(file_path)
        if gdf is None:
            raise ToolExecutionError(f"Unable to create GeoDataFrame from: {file_path.name}")

        return gdf
    except Exception as e:
        logger.info(f"Unable to create GeoDataFrame from: {file_path.name}", e)
        raise ToolExecutionError(f"Unable to create GeoDataFrame from: {file_path.name}")


def write_geo_data_frame(dataset_path: Path, dataset_gdf: gpd.GeoDataFrame) -> None:
    """
    Write a GeoDataFrame as a parquet file.

    :param dataset_path: the Path of the output file
    :param dataset_gdf: the dataset
    """
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    dataset_gdf.to_parquet(dataset_path)


def validate_dataset_crs(dataset: gpd.GeoDataFrame, georef: Georeference) -> None:
    """
    Validate and ensure a GeoDataFrame has a CRS set and is using EPSG:4326 coordinates.
    If the CRS is not set EPSG:4326 will be assumed and it will be set.

    :param dataset: GeoDataFrame to validate
    :param georef: Georeference for the dataset
    :raises ToolExecutionError: if the dataset uses an unsupported CRS
    """
    if dataset.crs is None:
        dataset.set_crs("EPSG:4326", inplace=True)
    elif dataset.crs != "EPSG:4326":
        raise ToolExecutionError(f"Dataset {georef} does not use a supported CRS. Only EPSG:4326 is supported.")


def create_derived_stac_item(
    derived_dataset_reference: Georeference,
    derived_dataset_title: str,
    derived_dataset_description: str,
    original_item: Item,
):
    """
    Create a new STAC Item for the result dataset. The new item will duplicate information from the original
    item when meaningful.

    :param derived_dataset_reference: the new georeference for the derived dataset
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

    filtered_dataset_item = Item(
        id=derived_dataset_reference.item_id,
        geometry=original_item.geometry,
        bbox=original_item.bbox,
        datetime=original_item.datetime,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        properties={
            "title": derived_dataset_title,
            "description": derived_dataset_description,
            "keywords": original_item.properties["keywords"],
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
