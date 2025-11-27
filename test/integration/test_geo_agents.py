# Copyright 2025 Amazon.com, Inc. or its affiliates.

"""Integration tests for GeoAgent MCP tools using pytest."""

import re

import pytest

from ..utils.logger import logger
from .test_mcp_client import MCPTestClient


def normalize_stac_references(text: str) -> str:
    """
    Normalize STAC references by replacing dynamic IDs with a placeholder.

    This allows comparison of results that contain dynamically generated STAC item IDs.
    Example: stac:cluster_features-MIQ9RE9Z -> stac:cluster_features-<ID>

    :param text: Text containing STAC references
    :return: Text with normalized STAC references
    """
    # Pattern matches stac:operation_name-ALPHANUMERIC_ID
    return re.sub(r"(stac:[a-z_]+-)[A-Z0-9]+", r"\1<ID>", text)


@pytest.mark.asyncio
async def test_buffer_geometry(mcp_client: MCPTestClient) -> None:
    """Test buffer_geometry tool - buffers POINT(0 0) by 100m distance."""
    logger.info("Test buffer_geometry")
    result = await mcp_client.invoke_tool_with_connection("buffer_geometry", {"geometry": "POINT(0 0)", "distance": 100.0})

    # Validate result matches expected output
    expected = (
        "The input geometry has been buffered by 100.0 meters. "
        "Result: POLYGON ((0.000897 0, 0.000777 -0.000452, 0.000449 -0.000782, 0 -0.000903, "
        "-0.000449 -0.000782, -0.000777 -0.000452, -0.000897 0, -0.000777 0.000452, "
        "-0.000449 0.000782, 0 0.000903, 0.000449 0.000782, 0.000777 0.000452, 0.000897 0))"
    )
    assert result == expected, f"Expected: {expected}\nActual: {result}"

    logger.info("\tPassed")


@pytest.mark.asyncio
async def test_translate_geometry(mcp_client: MCPTestClient) -> None:
    """Test translate_geometry tool - translates POINT(0 0) by 1000m at 90° heading."""
    logger.info("Test translate_geometry")
    result = await mcp_client.invoke_tool_with_connection(
        "translate_geometry", {"geometry": "POINT(0 0)", "distance": 1000.0, "heading": 90.0}
    )

    # Validate result matches expected output
    expected = "The input geometry has been translated by 1000.0 meters at heading 90.0 degrees. Result: POINT (0.008974 0)"
    assert result == expected, f"Expected: {expected}\nActual: {result}"

    logger.info("\tPassed")


@pytest.mark.asyncio
async def test_cluster_features(mcp_client: MCPTestClient, test_datasets: dict, stac_cleanup) -> None:
    """Test cluster_features tool - clusters earthquake points with 100km distance."""
    logger.info("Test cluster_features")
    result = await mcp_client.invoke_tool_with_connection(
        "cluster_features",
        {
            "dataset": test_datasets["recent_earthquakes"],
            "distance": 100000.0,  # 100km in meters
            "output_format": "geojson",
        },
    )

    # Track STAC references for cleanup
    stac_cleanup(result)

    # Validate result contains expected content
    assert result is not None, "Result should not be None"
    expected = (
        f"Found 21 clusters in dataset {test_datasets['recent_earthquakes']} "
        f"using a distance threshold of 100000.0 meters. \n"
        f"All clusters are available in stac:cluster_features-<ID> with the following assets:\n"
        f"- cluster-0: 60 features\n- cluster-2: 44 features\n- cluster-9: 23 features\n"
        f"- cluster-3: 14 features\n- cluster-4: 13 features\n- cluster-11: 13 features\n"
        f"- cluster-5: 10 features\n- cluster-12: 9 features\n- cluster-13: 6 features\n"
        f"- cluster-16: 5 features\n- cluster-19: 4 features\n- cluster-1: 3 features\n"
        f"- cluster-8: 3 features\n- cluster-14: 3 features\n- cluster-18: 3 features\n"
        f"- cluster-6: 2 features\n- cluster-7: 2 features\n- cluster-10: 2 features\n"
        f"- cluster-15: 2 features\n- cluster-17: 2 features\n- cluster-20: 2 features\n"
    )
    assert (
        normalize_stac_references(result) == expected
    ), f"Expected: {expected}\nActual: {normalize_stac_references(result)}"

    logger.info("\tPassed")


@pytest.mark.asyncio
async def test_correlate_datasets(mcp_client: MCPTestClient, test_datasets: dict, stac_cleanup) -> None:
    """Test correlate_datasets tool - correlates recent and significant earthquakes within 50km."""
    logger.info("Test correlate_datasets")
    result = await mcp_client.invoke_tool_with_connection(
        "correlate_datasets",
        {
            "dataset1": test_datasets["recent_earthquakes"],
            "dataset2": test_datasets["significant_earthquakes"],
            "distance": 50000.0,  # 50km in meters
            "geometry_operation": "left",
            "output_format": "geojson",
        },
    )

    # Track STAC references for cleanup
    stac_cleanup(result)

    # Validate result contains expected content
    assert result is not None, "Result should not be None"
    expected = (
        f"The datasets {test_datasets['recent_earthquakes']} and {test_datasets['significant_earthquakes']} "
        f"have been correlated using the intersection operation. "
        f"The correlated result is known as stac:correlate_datasets-<ID>#integ-test-recent_earthquakes.geojson. "
        f"A summary of the contents is: This dataset contains 17 features resulting from an intersection "
        f"correlation operation between {test_datasets['recent_earthquakes']} and "
        f"{test_datasets['significant_earthquakes']}. A buffer of 50000.0 units was applied to the first dataset."
    )
    assert (
        normalize_stac_references(result) == expected
    ), f"Expected: {expected}\nActual: {normalize_stac_references(result)}"

    logger.info("\tPassed")


@pytest.mark.asyncio
async def test_filter_dataset(mcp_client: MCPTestClient, test_datasets: dict, stac_cleanup) -> None:
    """Test filter_dataset tool - filters earthquakes within Pacific region polygon."""
    logger.info("Test filter_dataset")
    result = await mcp_client.invoke_tool_with_connection(
        "filter_dataset",
        {
            "dataset": test_datasets["recent_earthquakes"],
            "filter": "POLYGON((-180 -60, 180 -60, 180 60, -180 60, -180 -60))",  # Wide Pacific bounds
            "filter_type": "intersects",
            "output_format": "geojson",
        },
    )

    # Track STAC references for cleanup
    stac_cleanup(result)

    # Validate result contains expected content
    assert result is not None, "Result should not be None"
    expected = (
        f"The dataset {test_datasets['recent_earthquakes']} has been filtered. "
        f"The filtered result is known as stac:filter_dataset-<ID>#integ-test-recent_earthquakes.geojson. "
        f"A summary of the contents is: This dataset contains 233 features selected from "
        f"{test_datasets['recent_earthquakes']}. A intersects spatial filter against "
        f"POLYGON((-180 -60, 180 -60, 180 60, -180 60, -180 -60)) was applied. "
    )
    assert (
        normalize_stac_references(result) == expected
    ), f"Expected: {expected}\nActual: {normalize_stac_references(result)}"

    logger.info("\tPassed")


@pytest.mark.asyncio
async def test_sample_features(mcp_client: MCPTestClient, test_datasets: dict) -> None:
    """Test sample_features tool - samples 10 features from recent earthquakes."""
    logger.info("Test sample_features")
    result = await mcp_client.invoke_tool_with_connection(
        "sample_features", {"dataset": test_datasets["recent_earthquakes"], "number_of_features": 10}
    )

    # Validate result contains expected content
    assert result is not None, "Result should not be None"
    # Expected output contains table data - using multi-line string for readability
    expected = (
        f"Sample of 10 features from dataset {test_datasets['recent_earthquakes']} (total features: 266)\n\n"
        f"| id | mag | place | time | updated | tz | url | detail | felt | cdi | mmi | alert | status | tsunami | "
        f"sig | net | code | ids | sources | types | nst | dmin | rms | gap | magType | type | title | geometry |\n"
        f"| -- | --- | ----- | ---- | ------- | -- | --- | ------ | ---- | --- | --- | ----- | ------ | ------- | "
        f"--- | --- | ---- | --- | ------- | ----- | --- | ---- | --- | --- | ------- | ---- | ----- | -------- |\n"
        f"| ci41128991 | 0.7 | 9 km SW of Idyllw... | 1764364985710 | 1764365213780 | None | https://earthquak... | "
        f"https://earthquak... | nan | nan | nan | None | automatic | 0 | 8 | ci | 41128991 | ,ci41128991, | ,ci, | "
        f",nearby-cities,or... | 29 | 0.07126 | 0.14 | 79.0 | ml | earthquake | M 0.7 - 9 km SW o... | "
        f"POINT (-116.79116... |\n"
        f"| ak2025xlfwqw | 1.491728092186685 | 19 km NNE of Cant... | 1764364961536 | 1764365068843 | None | "
        f"https://earthquak... | https://earthquak... | nan | nan | nan | None | automatic | 0 | 34 | ak | 2025xlfwqw | "
        f",ak2025xlfwqw, | ,ak, | ,origin,phase-data, | 18 | 0.14840199053287506 | 0.7787067462026575 | "
        f"48.46404266357422 | ml | earthquake | M 1.5 - 19 km NNE... | POINT (-148.77713... |\n"
        f"| ak2025xlfnoi | 2.057918946347115 | 28 km ENE of Susi... | 1764364359103 | 1764364489601 | None | "
        f"https://earthquak... | https://earthquak... | nan | nan | nan | None | automatic | 0 | 65 | ak | 2025xlfnoi | "
        f",ak2025xlfnoi, | ,ak, | ,origin,phase-data, | 47 | 0.42671528458595276 | 1.0857624414685711 | "
        f"36.267608642578125 | ml | earthquake | M 2.1 - 28 km ENE... | POINT (-149.38293... |\n"
        f"| nc75271226 | 1.04 | 8 km NW of The Ge... | 1764363705720 | 1764363872183 | None | https://earthquak... | "
        f"https://earthquak... | nan | nan | nan | None | automatic | 0 | 17 | nc | 75271226 | ,nc75271226, | ,nc, | "
        f",nearby-cities,or... | 11 | 0.01428 | 0.01 | 77.0 | md | earthquake | M 1.0 - 8 km NW o... | "
        f"POINT (-122.81816... |\n"
        f"| nc75271216 | 1.53 | 8 km W of Cobb, CA | 1764363701940 | 1764363796989 | None | https://earthquak... | "
        f"https://earthquak... | nan | nan | nan | None | automatic | 0 | 36 | nc | 75271216 | ,nc75271216, | ,nc, | "
        f",nearby-cities,or... | 8 | 0.01962 | 0.02 | 92.0 | md | earthquake | M 1.5 - 8 km W of... | "
        f"POINT (-122.81383... |\n"
        f"| nc75271221 | 1.64 | 8 km W of Cobb, CA | 1764363660130 | 1764363932430 | None | https://earthquak... | "
        f"https://earthquak... | nan | nan | nan | None | automatic | 0 | 41 | nc | 75271221 | ,nc75271221, | ,nc, | "
        f",focal-mechanism,... | 32 | 0.01483 | 0.03 | 61.0 | md | earthquake | M 1.6 - 8 km W of... | "
        f"POINT (-122.81716... |\n"
        f"| nc75271211 | 1.04 | 8 km NW of The Ge... | 1764363614950 | 1764363712476 | None | https://earthquak... | "
        f"https://earthquak... | nan | nan | nan | None | automatic | 0 | 17 | nc | 75271211 | ,nc75271211, | ,nc, | "
        f",nearby-cities,or... | 20 | 0.01396 | 0.01 | 63.0 | md | earthquake | M 1.0 - 8 km NW o... | "
        f"POINT (-122.81833... |\n"
        f"| hv74840982 | 1.78 | 13 km SSE of Volc... | 1764362452080 | 1764362683270 | None | https://earthquak... | "
        f"https://earthquak... | nan | nan | nan | None | automatic | 0 | 49 | hv | 74840982 | ,hv74840982, | ,hv, | "
        f",origin,phase-data, | 41 | 0.04777 | 0.209999993 | 163.0 | md | earthquake | M 1.8 - 13 km SSE... | "
        f"POINT (-155.17216... |\n"
        f"| ak2025xldzur | 2.4002551909577656 | 42 km NNW of Vald... | 1764361560898 | 1764361669604 | None | "
        f"https://earthquak... | https://earthquak... | nan | nan | nan | None | automatic | 0 | 89 | ak | 2025xldzur | "
        f",ak2025xldzur, | ,ak, | ,origin,phase-data, | 47 | 0.3122054934501648 | 0.8197908820744363 | "
        f"29.347291946411133 | ml | earthquake | M 2.4 - 42 km NNW... | POINT (-146.57345... |\n"
        f"| ci41128975 | 0.68 | 7 km SSE of Hemet... | 1764361150060 | 1764361373564 | None | https://earthquak... | "
        f"https://earthquak... | nan | nan | nan | None | automatic | 0 | 7 | ci | 41128975 | ,ci41128975, | ,ci, | "
        f",nearby-cities,or... | 20 | 0.02715 | 0.12 | 79.0 | ml | earthquake | M 0.7 - 7 km SSE ... | "
        f"POINT (-116.95633... |"
    )
    assert result == expected, f"Expected: {expected}\nActual: {result}"

    logger.info("\tPassed")


@pytest.mark.asyncio
async def test_summarize_dataset(mcp_client: MCPTestClient, test_datasets: dict) -> None:
    """Test summarize_dataset tool - summarizes recent earthquakes dataset."""
    logger.info("Test summarize_dataset")
    result = await mcp_client.invoke_tool_with_connection(
        "summarize_dataset", {"dataset": test_datasets["recent_earthquakes"]}
    )

    # Validate result contains expected content
    assert result is not None, "Result should not be None"
    expected = (
        f"Dataset {test_datasets['recent_earthquakes']} contains 266 features.\n"
        f"- Dataset bounds (min_x, min_y, max_x, max_y): -179.198000, -37.247700, 158.629200, 65.060829\n"
        f"Columns:\n"
        f"- geometry: Contains spatial features of type(s): Point\n- id: General column\n"
        f"- mag: Numeric column (float64) ranging from -0.11 to 5.8\n- place: General column\n"
        f"- time: Numeric column (int64) ranging from 1764279563860 to 1764364985710\n"
        f"- updated: Numeric column (int64) ranging from 1764279878530 to 1764365321135\n"
        f"- tz: General column\n- url: General column\n- detail: General column\n"
        f"- felt: Numeric column (float64) ranging from 0.0 to 651.0\n"
        f"- cdi: Numeric column (float64) ranging from 0.0 to 4.6\n"
        f"- mmi: Numeric column (float64) ranging from 1.731 to 3.895\n"
        f"- alert: General column\n- status: General column\n- tsunami: Column of type int32\n"
        f"- sig: Column of type int32\n- net: General column\n- code: General column\n"
        f"- ids: General column\n- sources: General column\n- types: General column\n"
        f"- nst: Column of type int32\n"
        f"- dmin: Numeric column (float64) ranging from 0.0 to 29.405\n"
        f"- rms: Numeric column (float64) ranging from 0.0 to 1.2574613187411168\n"
        f"- gap: Numeric column (float64) ranging from 14.0 to 306.0\n"
        f"- magType: General column\n- type: General column\n- title: General column"
    )
    assert result == expected, f"Expected: {expected}\nActual: {result}"

    logger.info("\tPassed")


@pytest.mark.asyncio
async def test_append_datasets(mcp_client: MCPTestClient, test_datasets: dict, stac_cleanup) -> None:
    """Test append_datasets tool - appends recent and significant earthquake datasets."""
    logger.info("Test append_datasets")
    result = await mcp_client.invoke_tool_with_connection(
        "append_datasets",
        {
            "datasets": [test_datasets["recent_earthquakes"], test_datasets["significant_earthquakes"]],
            "output_format": "geojson",
        },
    )

    # Track STAC references for cleanup
    stac_cleanup(result)

    # Validate result contains expected content
    assert result is not None, "Result should not be None"
    expected = (
        f"The 2 datasets have been combined into a single dataset. "
        f"The combined result is known as stac:append_datasets-<ID>#combined. "
        f"A summary of the contents is: This dataset contains 278 features resulting from appending 2 datasets: "
        f"Dataset from {test_datasets['recent_earthquakes']}, "
        f"Dataset from {test_datasets['significant_earthquakes']}."
    )
    assert (
        normalize_stac_references(result) == expected
    ), f"Expected: {expected}\nActual: {normalize_stac_references(result)}"

    logger.info("\tPassed")
