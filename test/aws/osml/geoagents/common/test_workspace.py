#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import os
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import boto3
import geopandas as gpd
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from fsspec.implementations.local import LocalFileSystem
from moto import mock_aws
from pystac import Item
from s3fs import S3FileSystem
from shapely.geometry import Point

from aws.osml.geoagents.common import Workspace


class TestWorkspace(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test method"""

        self.mock_aws = mock_aws()
        self.mock_aws.start()

        self.s3 = boto3.client("s3")
        self.bucket_name = "XXXXXXXXXXXXXXXXXXXXX"
        self.user_id = "shared"

        # Initialize workspace with S3 filesystem
        self.s3.create_bucket(Bucket=self.bucket_name)
        self.s3fs = S3FileSystem(anon=False)
        self.prefix = f"{self.bucket_name}/{self.user_id}"
        self.workspace = Workspace(filesystem=self.s3fs, prefix=self.prefix)

        # Also create a local filesystem workspace for testing
        self.local_fs = LocalFileSystem()
        self.tmp_path = tempfile.mkdtemp()
        self.local_workspace_path = Path(self.tmp_path) / "local_workspace"
        self.local_workspace_path.mkdir(exist_ok=True)
        self.local_workspace = Workspace(filesystem=self.local_fs, prefix=str(self.local_workspace_path))

    def tearDown(self):
        """Clean up after each test method"""
        # Clean up local files
        shutil.rmtree(self.tmp_path)

        self.mock_aws.stop()

    def create_sample_stac_item(self):
        """Helper method to create a sample STAC item"""
        return Item(
            id="012345",
            geometry={"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
            bbox=[0, 0, 1, 1],
            datetime=datetime.fromisoformat("2025-04-23T14:05:23Z"),
            properties={},
        )

    @unittest.skip("Moto and S3FS do not work well together")
    def test_s3_filesystem(self):
        """Test using a local filesystem"""
        # Create a sample STAC item
        sample_item = self.create_sample_stac_item()

        # Create a test asset file
        test_asset_path = Path(self.tmp_path, "local-test-asset.txt")
        test_content = b"local test file content"
        with open(test_asset_path, "wb") as out:
            out.write(test_content)

        local_assets = {"local-test-asset": test_asset_path}

        # Publish the item to the local workspace
        stac_ref = self.workspace.create_item(sample_item, local_assets)
        assert stac_ref is not None

        # Verify the item was published
        item_path = Path(self.prefix) / "stac" / sample_item.id / "item.json"
        assert self.s3fs.exists(item_path)

        # Verify the asset was published
        asset_path = Path(self.prefix) / "stac" / sample_item.id / "local-test-asset" / test_asset_path.name
        assert self.s3fs.exists(asset_path)

        # Test get_item
        retrieved_item = self.workspace.get_item(stac_ref)
        assert retrieved_item.id == sample_item.id
        assert "local-test-asset" in retrieved_item.assets

        # Test list_items
        items = self.workspace.list_items()
        assert len(items) == 1
        assert items[0].item_id == sample_item.id

        # Test delete_item
        self.workspace.delete_item(stac_ref)
        assert not self.s3fs.exists(str(Path(self.prefix) / "stac" / sample_item.id))

    def test_local_filesystem(self):
        """Test using a local filesystem"""
        # Create a sample STAC item
        sample_item = self.create_sample_stac_item()

        # Create a test asset file
        test_asset_path = Path(self.tmp_path, "local-test-asset.txt")
        test_content = b"local test file content"
        with open(test_asset_path, "wb") as out:
            out.write(test_content)

        local_assets = {"local-test-asset": test_asset_path}

        # Publish the item to the local workspace
        stac_ref = self.local_workspace.create_item(sample_item, local_assets)
        assert stac_ref is not None

        # Verify the item was published
        item_path = Path(self.local_workspace_path) / "stac" / sample_item.id / "item.json"
        assert item_path.exists()

        # Verify the asset was published
        asset_path = Path(self.local_workspace_path) / "stac" / sample_item.id / "local-test-asset" / test_asset_path.name
        assert asset_path.exists()
        assert asset_path.read_bytes() == test_content

        # Test get_item
        retrieved_item = self.local_workspace.get_item(stac_ref)
        assert retrieved_item.id == sample_item.id
        assert "local-test-asset" in retrieved_item.assets

        # Test list_items
        items = self.local_workspace.list_items()
        assert len(items) == 1
        assert items[0].item_id == sample_item.id

        # Test delete_item
        self.local_workspace.delete_item(stac_ref)
        assert not Path(self.local_workspace_path, "stac", sample_item.id).exists()

    def test_is_parquet_file_true(self):
        """Test is_parquet_file with a valid Parquet file."""
        # Create a file with PAR1 magic bytes
        file_path = os.path.join(self.tmp_path, "test.parquet")
        with open(file_path, "wb") as f:
            f.write(b"PAR1")  # Write the magic bytes

        # Test the function
        result = self.local_workspace.is_parquet_file(file_path)
        self.assertTrue(result)

    def test_is_parquet_file_false(self):
        """Test is_parquet_file with a non-Parquet file."""
        # Create a file with non-PAR1 magic bytes
        file_path = os.path.join(self.tmp_path, "test.txt")
        with open(file_path, "wb") as f:
            f.write(b"TEXT")  # Write non-Parquet content

        # Test the function
        result = self.local_workspace.is_parquet_file(file_path)
        self.assertFalse(result)

    def test_is_parquet_file_error(self):
        """Test is_parquet_file with a file that doesn't exist."""
        # Create a path to a file that doesn't exist
        file_path = os.path.join(self.tmp_path, "nonexistent.parquet")

        # Test the function with a nonexistent file
        result = self.local_workspace.is_parquet_file(file_path)
        self.assertFalse(result)

    def create_parquet_file_with_metadata(self, file_path, data=None, metadata=None):
        """Helper method to create a Parquet file with metadata."""
        if data is None:
            data = {"test_field": [1, 2, 3]}

        if metadata is None:
            metadata = {"test_field": "Test description"}

        # Create a pandas DataFrame
        df = pd.DataFrame(data)

        # Convert to PyArrow Table with metadata
        schema = pa.Schema.from_pandas(df)
        for field_name, description in metadata.items():
            if field_name in schema.names:
                field_index = schema.get_field_index(field_name)
                field = schema.field(field_index)
                field = field.with_metadata({b"comment": description.encode("utf-8")})
                schema = schema.set(field_index, field)

        table = pa.Table.from_pandas(df, schema=schema)

        # Write to Parquet file
        pq.write_table(table, file_path)
        return file_path

    def create_geo_data_frame(self):
        """Helper method to create a sample GeoDataFrame."""
        # Create a simple GeoDataFrame with points
        points = [Point(0, 0), Point(1, 1), Point(2, 2)]
        data = {"id": [1, 2, 3], "value": [10, 20, 30]}
        return gpd.GeoDataFrame(data, geometry=points)

    def create_geo_parquet_file(self, file_path, metadata=None):
        """Helper method to create a GeoParquet file with metadata."""
        gdf = self.create_geo_data_frame()

        # Use geopandas to_parquet which handles geometry columns correctly
        gdf.to_parquet(file_path)

        # If metadata is provided, we need to add it after the file is created
        if metadata:
            # Read the parquet file schema
            table = pq.read_table(file_path)
            schema = table.schema

            # Add metadata to fields
            for field_name, description in metadata.items():
                if field_name in schema.names:
                    field_index = schema.get_field_index(field_name)
                    field = schema.field(field_index)
                    field = field.with_metadata({b"comment": description.encode("utf-8")})
                    schema = schema.set(field_index, field)

            # Write the table back with updated schema
            table = table.cast(schema)
            pq.write_table(table, file_path)

        return gdf

    def create_geojson_file(self, file_path):
        """Helper method to create a GeoJSON file."""
        gdf = self.create_geo_data_frame()
        gdf.to_file(file_path, driver="GeoJSON")
        return gdf

    def test_read_field_descriptions_from_parquet(self):
        """Test read_field_descriptions_from_parquet."""
        # Create a real Parquet file with metadata
        file_path = os.path.join(self.tmp_path, "test.parquet")
        metadata = {"test_field": "Test description"}
        self.create_parquet_file_with_metadata(file_path, metadata=metadata)

        # Test the function
        result = self.local_workspace.read_field_descriptions_from_parquet(file_path)

        # Verify the result
        self.assertEqual(result, metadata)

    def test_read_geo_data_frame_parquet(self):
        """Test read_geo_data_frame with a Parquet file."""
        # Create a real GeoParquet file with metadata
        file_path = os.path.join(self.tmp_path, "test.parquet")
        metadata = {"value": "Test value description"}
        self.create_geo_parquet_file(file_path, metadata=metadata)

        # Test the function
        result = self.local_workspace.read_geo_data_frame(file_path)

        # Verify the result
        self.assertIsInstance(result, gpd.GeoDataFrame)
        self.assertEqual(len(result), 3)  # Should have 3 rows
        self.assertTrue("geometry" in result.columns)
        self.assertTrue("id" in result.columns)
        self.assertTrue("value" in result.columns)
        self.assertEqual(result.attrs.get("column-descriptions"), metadata)

    def test_read_geo_data_frame_non_parquet(self):
        """Test read_geo_data_frame with a non-Parquet file."""
        # Create a real GeoJSON file
        file_path = os.path.join(self.tmp_path, "test.geojson")
        self.create_geojson_file(file_path)

        # Test the function
        result = self.local_workspace.read_geo_data_frame(file_path)

        # Verify the result
        self.assertIsInstance(result, gpd.GeoDataFrame)
        self.assertEqual(len(result), 3)  # Should have 3 rows
        self.assertTrue("geometry" in result.columns)
        self.assertTrue("id" in result.columns)
        self.assertTrue("value" in result.columns)

    def test_read_geo_data_frame_error(self):
        """Test read_geo_data_frame with a file that doesn't exist."""
        # Create a path to a file that doesn't exist
        file_path = os.path.join(self.tmp_path, "nonexistent.parquet")

        # Test the function with a nonexistent file
        with self.assertRaises(ValueError):
            self.local_workspace.read_geo_data_frame(file_path)

    def test_read_geo_data_frame_wkt(self):
        """Test read_geo_data_frame with a WKT file."""
        # Create a WKT file with a simple polygon
        file_path = os.path.join(self.tmp_path, "test.wkt")
        wkt_content = "POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))"
        with open(file_path, "w") as f:
            f.write(wkt_content)

        # Test the function
        result = self.local_workspace.read_geo_data_frame(file_path)

        # Verify the result
        self.assertIsInstance(result, gpd.GeoDataFrame)
        self.assertEqual(len(result), 1)  # Should have 1 row
        self.assertEqual(result.crs, "EPSG:4326")  # CRS should be set to EPSG:4326
        self.assertEqual(result.geometry[0].wkt, wkt_content)  # Geometry should match input

    def test_geo_data_frame_io_geoparquet(self):
        """Test write_geo_data_frame with GeoParquet format."""
        # Create a sample GeoDataFrame
        sample_gdf = self.create_geo_data_frame()

        # Create a file path
        file_path = os.path.join(self.tmp_path, "test_output.parquet")

        # Write the GeoDataFrame to the file
        self.local_workspace.write_geo_data_frame(file_path, sample_gdf)

        # Verify the file was created
        self.assertTrue(os.path.exists(file_path))

        # Read the file back and verify the contents
        result = self.local_workspace.read_geo_data_frame(file_path)

        # Verify the result
        self.assertIsInstance(result, gpd.GeoDataFrame)
        self.assertEqual(len(result), 3)  # Should have 3 rows
        self.assertTrue("geometry" in result.columns)
        self.assertTrue("id" in result.columns)
        self.assertTrue("value" in result.columns)

    def test_geo_data_frame_io_geojson(self):
        """Test write_geo_data_frame with GeoJSON format."""
        # Create a sample GeoDataFrame
        sample_gdf = self.create_geo_data_frame()

        # Create a file path with .geojson extension
        file_path = os.path.join(self.tmp_path, "test_output.geojson")

        # Write the GeoDataFrame to the file
        self.local_workspace.write_geo_data_frame(file_path, sample_gdf)

        # Verify the file can be read back in
        result = self.local_workspace.read_geo_data_frame(file_path)

        # Verify the result
        self.assertIsInstance(result, gpd.GeoDataFrame)
        self.assertEqual(len(result), 3)  # Should have 3 rows
        self.assertTrue("geometry" in result.columns)
        self.assertTrue("id" in result.columns)
        self.assertTrue("value" in result.columns)

    def test_stac_reference_with_collections(self):
        """Test workspace with STACReference that includes collections."""
        # Create a sample STAC item
        sample_item = self.create_sample_stac_item()

        # Create a test asset file
        test_asset_path = Path(self.tmp_path, "collection-test-asset.txt")
        test_content = b"collection test file content"
        with open(test_asset_path, "wb") as out:
            out.write(test_content)

        local_assets = {"collection-test-asset": test_asset_path}
        collections = ["collection1", "collection2"]

        # Publish the item to the local workspace with collections
        stac_ref = self.local_workspace.create_item(sample_item, local_assets, collections=collections)
        assert stac_ref is not None

        # Verify the collections in the returned STACReference
        self.assertEqual(stac_ref.collections, collections)
        self.assertEqual(stac_ref.item_id, sample_item.id)

        # Verify the item was published in the correct collection path
        collections_path = "/".join(collections)
        item_path = Path(self.local_workspace_path) / "stac" / collections_path / sample_item.id / "item.json"
        assert item_path.exists()

        # Verify the asset was published in the correct collection path
        asset_path = (
            Path(self.local_workspace_path)
            / "stac"
            / collections_path
            / sample_item.id
            / "collection-test-asset"
            / test_asset_path.name
        )
        assert asset_path.exists()
        assert asset_path.read_bytes() == test_content

        # Test get_item with collections
        retrieved_item = self.local_workspace.get_item(stac_ref)
        assert retrieved_item.id == sample_item.id
        assert "collection-test-asset" in retrieved_item.assets

        # Test delete_item with collections
        self.local_workspace.delete_item(stac_ref)
        assert not Path(self.local_workspace_path, "stac", collections_path, sample_item.id).exists()

    def test_combine_geometry_columns_single(self):
        """Test combine_geometry_columns with a GeoDataFrame that has a single geometry column."""
        # Create a simple GeoDataFrame with one geometry column
        gdf = self.create_geo_data_frame()

        # Call the function
        result = self.local_workspace.combine_geometry_columns(gdf)

        # Verify the result is the same as the input (no changes)
        self.assertIs(result, gdf)
        self.assertEqual(len(result.columns[result.dtypes == "geometry"]), 1)

    def test_combine_geometry_columns_multiple(self):
        """Test combine_geometry_columns with a GeoDataFrame that has multiple geometry columns."""
        from shapely.geometry import GeometryCollection, LineString, Point

        # Create a GeoDataFrame with multiple geometry columns
        points = [Point(0, 0), Point(1, 1), Point(2, 2)]
        lines = [LineString([(0, 0), (1, 1)]), LineString([(1, 1), (2, 2)]), LineString([(2, 2), (3, 3)])]
        data = {"id": [1, 2, 3], "value": [10, 20, 30]}

        # Create the GeoDataFrame with the first geometry column
        gdf = gpd.GeoDataFrame(data, geometry=points)

        # Add a second geometry column
        gdf["lines"] = gpd.GeoSeries(lines)
        gdf.set_geometry("geometry")  # Ensure the active geometry column is the first one

        # Verify we have two geometry columns
        self.assertEqual(len(gdf.columns[gdf.dtypes == "geometry"]), 2)

        # Call the function
        result = self.local_workspace.combine_geometry_columns(gdf)

        # Verify the result has only one geometry column
        self.assertEqual(len(result.columns[result.dtypes == "geometry"]), 1)
        self.assertEqual(result.geometry.name, "geometry")

        # Verify the geometry column contains GeometryCollection objects
        for i, geom in enumerate(result.geometry):
            self.assertIsInstance(geom, GeometryCollection)
            # For GeometryCollection, we can convert to WKT and verify it contains both geometries
            wkt = geom.wkt
            self.assertIn("POINT", wkt)
            self.assertIn("LINESTRING", wkt)
        # Verify other columns are preserved
        self.assertTrue("id" in result.columns)
        self.assertTrue("value" in result.columns)
        self.assertEqual(list(result["id"]), [1, 2, 3])
        self.assertEqual(list(result["value"]), [10, 20, 30])

    def test_combine_geometry_columns_with_nested_collections(self):
        """Test combine_geometry_columns with nested GeometryCollections."""
        from shapely.geometry import GeometryCollection, LineString, Point, Polygon

        # Create a simple point and line
        point = Point(0, 0)
        line = LineString([(1, 1), (2, 2)])

        # Create a nested GeometryCollection
        nested_collection = GeometryCollection(
            [Point(3, 3), GeometryCollection([Point(4, 4), LineString([(5, 5), (6, 6)])])]
        )

        # Create a polygon
        polygon = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])

        # Create a GeoDataFrame with these geometries
        data = {"id": [1], "value": [10]}
        gdf = gpd.GeoDataFrame(data, geometry=[point])

        # Add additional geometry columns
        gdf["lines"] = gpd.GeoSeries([line])
        gdf["nested"] = gpd.GeoSeries([nested_collection])
        gdf["polygons"] = gpd.GeoSeries([polygon])

        # Verify we have four geometry columns
        self.assertEqual(len(gdf.columns[gdf.dtypes == "geometry"]), 4)

        # Call the function
        result = self.local_workspace.combine_geometry_columns(gdf)

        # Verify the result has only one geometry column
        self.assertEqual(len(result.columns[result.dtypes == "geometry"]), 1)

        # Get the resulting geometry and verify it's a GeometryCollection
        combined_geom = result.geometry[0]
        self.assertIsInstance(combined_geom, GeometryCollection)

        # The combined geometry should have 6 geometries (not nested):
        # 1. Point(0, 0)
        # 2. LineString([(1, 1), (2, 2)])
        # 3. Point(3, 3)
        # 4. Point(4, 4)
        # 5. LineString([(5, 5), (6, 6)])
        # 6. Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])

        # Use WKT to verify the content since type checking is causing issues with geoms attribute
        wkt = combined_geom.wkt
        self.assertIn("POINT", wkt)
        self.assertIn("LINESTRING", wkt)
        self.assertIn("POLYGON", wkt)

        # We can't directly access the geometries due to type checking issues,
        # but we can verify the result by checking that:
        # 1. The result is a GeometryCollection (already verified above)
        # 2. The WKT representation contains all expected geometry types (verified above)
        # 3. There are no nested GeometryCollections in the WKT
        self.assertNotIn("GEOMETRYCOLLECTION (GEOMETRYCOLLECTION", wkt)

        # Count occurrences of each geometry type in the WKT
        # This is a rough approximation but should work for this test
        point_count = wkt.count("POINT")
        linestring_count = wkt.count("LINESTRING")
        polygon_count = wkt.count("POLYGON")

        # Verify all original geometries are present in the flattened collection
        self.assertEqual(point_count, 3)  # Three points
        self.assertEqual(linestring_count, 2)  # Two lines
        self.assertEqual(polygon_count, 1)  # One polygon
