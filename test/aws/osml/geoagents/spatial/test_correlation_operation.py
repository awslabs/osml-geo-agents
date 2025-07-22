#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import geopandas as gpd
import shapely
from pystac import Item

from aws.osml.geoagents.common import GeoDataReference, STACReference, Workspace
from aws.osml.geoagents.spatial.correlation_operation import GeometryOperationType, correlation_operation


class TestCorrelationOperation(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a mock workspace
        self.mock_workspace = Mock(spec=Workspace)
        self.mock_workspace.session_local_path = "/tmp"

        # Create mock GeoDataReferences
        self.dataset1_reference = Mock(spec=GeoDataReference)
        self.dataset1_reference.reference_string = "stac:test-dataset1"
        self.dataset1_reference.is_stac_reference = Mock(return_value=True)

        self.dataset2_reference = Mock(spec=GeoDataReference)
        self.dataset2_reference.reference_string = "stac:test-dataset2"
        self.dataset2_reference.is_stac_reference = Mock(return_value=True)

        # Create a mock function name
        self.function_name = "CORRELATE"

        # Create a mock distance
        self.distance = 100.0

        # Create mock geo column names
        self.dataset1_geo_column = "geometry"
        self.dataset2_geo_column = "geometry"

    @patch("aws.osml.geoagents.spatial.correlation_operation.LocalAssets")
    @patch("aws.osml.geoagents.spatial.correlation_operation.create_derived_stac_item")
    @patch("aws.osml.geoagents.spatial.correlation_operation.create_stac_item_for_dataset")
    @patch("aws.osml.geoagents.spatial.correlation_operation.STACReference")
    def test_correlation_operation(
        self, mock_stac_reference, mock_create_stac_item_for_dataset, mock_create_derived_stac_item, mock_local_assets
    ):
        """Test successful correlation."""
        # Set up mocks for LocalAssets context manager
        mock_item1 = Mock(spec=Item)
        mock_item1.properties = {"title": "Test Dataset 1"}
        mock_local_asset_paths1 = {"asset1": Path("/tmp/asset1.parquet")}

        mock_item2 = Mock(spec=Item)
        mock_item2.properties = {"title": "Test Dataset 2"}
        mock_local_asset_paths2 = {"asset2": Path("/tmp/asset2.parquet")}

        # Configure the LocalAssets mock to return different values on each call
        mock_local_assets.return_value.__enter__.side_effect = [
            (mock_item1, mock_local_asset_paths1),
            (mock_item2, mock_local_asset_paths2),
        ]

        # Create mock GeoDataFrames with overlapping polygons
        polygon1 = shapely.Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
        polygon2 = shapely.Polygon([(0.5, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 1.5), (0.5, 0.5)])

        gdf1 = gpd.GeoDataFrame(geometry=[polygon1])
        gdf1.crs = "EPSG:4326"

        gdf2 = gpd.GeoDataFrame(geometry=[polygon2])
        gdf2.crs = "EPSG:4326"

        # Configure read_geo_data_frame to return different GeoDataFrames on each call
        self.mock_workspace.read_geo_data_frame.side_effect = [gdf1, gdf2]

        # Set up mock for create_derived_stac_item
        mock_derived_item = Mock(spec=Item)
        mock_create_derived_stac_item.return_value = mock_derived_item

        # Set up mock for create_stac_item_for_dataset
        mock_create_stac_item_for_dataset.return_value = mock_item1

        # Set up mock for STACReference
        mock_stac_ref = Mock(spec=STACReference)
        mock_stac_ref.item_id = "test-item-id"
        mock_stac_reference.new_from_timestamp.return_value = mock_stac_ref

        # Call the operation function
        result = correlation_operation(
            dataset1_reference=self.dataset1_reference,
            dataset2_reference=self.dataset2_reference,
            distance=self.distance,
            dataset1_geo_column=self.dataset1_geo_column,
            dataset2_geo_column=self.dataset2_geo_column,
            workspace=self.mock_workspace,
            function_name=self.function_name,
        )

        # Verify the result contains expected text
        self.assertIn("correlated", result)
        self.assertIn("intersection", result)

        # Verify the mocks were called
        self.assertEqual(mock_local_assets.call_count, 2)
        self.assertEqual(self.mock_workspace.read_geo_data_frame.call_count, 2)
        self.mock_workspace.write_geo_data_frame.assert_called_once()
        mock_create_derived_stac_item.assert_called_once()
        self.mock_workspace.create_item.assert_called_once()

    @patch("aws.osml.geoagents.spatial.correlation_operation.LocalAssets")
    @patch("aws.osml.geoagents.spatial.correlation_operation.create_derived_stac_item")
    @patch("aws.osml.geoagents.spatial.correlation_operation.create_stac_item_for_dataset")
    @patch("aws.osml.geoagents.spatial.correlation_operation.STACReference")
    def test_correlation_operation_right_geometry(
        self, mock_stac_reference, mock_create_stac_item_for_dataset, mock_create_derived_stac_item, mock_local_assets
    ):
        """Test intersection correlation with RIGHT geometry operation."""
        # Set up mocks for LocalAssets context manager
        mock_item1 = Mock(spec=Item)
        mock_item1.properties = {"title": "Test Dataset 1"}
        mock_local_asset_paths1 = {"asset1": Path("/tmp/asset1.parquet")}

        mock_item2 = Mock(spec=Item)
        mock_item2.properties = {"title": "Test Dataset 2"}
        mock_local_asset_paths2 = {"asset2": Path("/tmp/asset2.parquet")}

        # Configure the LocalAssets mock to return different values on each call
        mock_local_assets.return_value.__enter__.side_effect = [
            (mock_item1, mock_local_asset_paths1),
            (mock_item2, mock_local_asset_paths2),
        ]

        # Create mock GeoDataFrames with overlapping polygons
        polygon1 = shapely.Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
        polygon2 = shapely.Polygon([(0.5, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 1.5), (0.5, 0.5)])

        gdf1 = gpd.GeoDataFrame(geometry=[polygon1])
        gdf1.crs = "EPSG:4326"

        gdf2 = gpd.GeoDataFrame(geometry=[polygon2])
        gdf2.crs = "EPSG:4326"

        # Configure read_geo_data_frame to return different GeoDataFrames on each call
        self.mock_workspace.read_geo_data_frame.side_effect = [gdf1, gdf2]

        # Set up mock for create_derived_stac_item
        mock_derived_item = Mock(spec=Item)
        mock_create_derived_stac_item.return_value = mock_derived_item

        # Set up mock for create_stac_item_for_dataset
        mock_create_stac_item_for_dataset.return_value = mock_item1

        # Set up mock for STACReference
        mock_stac_ref = Mock(spec=STACReference)
        mock_stac_ref.item_id = "test-item-id"
        mock_stac_reference.new_from_timestamp.return_value = mock_stac_ref

        # Call the operation function with RIGHT geometry operation
        result = correlation_operation(
            dataset1_reference=self.dataset1_reference,
            dataset2_reference=self.dataset2_reference,
            distance=self.distance,
            dataset1_geo_column=self.dataset1_geo_column,
            dataset2_geo_column=self.dataset2_geo_column,
            workspace=self.mock_workspace,
            function_name=self.function_name,
            geometry_operation=GeometryOperationType.RIGHT,
        )

        # Verify the result contains expected text
        self.assertIn("correlated", result)
        self.assertIn("intersection", result)
        self.assertIn("'right' geometry operation", result)

        # Verify the mocks were called
        self.assertEqual(mock_local_assets.call_count, 2)
        self.assertEqual(self.mock_workspace.read_geo_data_frame.call_count, 2)
        self.mock_workspace.write_geo_data_frame.assert_called_once()
        mock_create_derived_stac_item.assert_called_once()
        self.mock_workspace.create_item.assert_called_once()

    @patch("aws.osml.geoagents.spatial.correlation_operation.LocalAssets")
    @patch("aws.osml.geoagents.spatial.correlation_operation.create_derived_stac_item")
    @patch("aws.osml.geoagents.spatial.correlation_operation.create_stac_item_for_dataset")
    @patch("aws.osml.geoagents.spatial.correlation_operation.STACReference")
    def test_correlation_operation_collect_geometry(
        self, mock_stac_reference, mock_create_stac_item_for_dataset, mock_create_derived_stac_item, mock_local_assets
    ):
        """Test intersection correlation with COLLECT geometry operation."""
        # Set up mocks for LocalAssets context manager
        mock_item1 = Mock(spec=Item)
        mock_item1.properties = {"title": "Test Dataset 1"}
        mock_local_asset_paths1 = {"asset1": Path("/tmp/asset1.parquet")}

        mock_item2 = Mock(spec=Item)
        mock_item2.properties = {"title": "Test Dataset 2"}
        mock_local_asset_paths2 = {"asset2": Path("/tmp/asset2.parquet")}

        # Configure the LocalAssets mock to return different values on each call
        mock_local_assets.return_value.__enter__.side_effect = [
            (mock_item1, mock_local_asset_paths1),
            (mock_item2, mock_local_asset_paths2),
        ]

        # Create mock GeoDataFrames with overlapping polygons
        polygon1 = shapely.Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
        polygon2 = shapely.Polygon([(0.5, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 1.5), (0.5, 0.5)])

        gdf1 = gpd.GeoDataFrame(geometry=[polygon1])
        gdf1.crs = "EPSG:4326"

        gdf2 = gpd.GeoDataFrame(geometry=[polygon2])
        gdf2.crs = "EPSG:4326"

        # Configure read_geo_data_frame to return different GeoDataFrames on each call
        self.mock_workspace.read_geo_data_frame.side_effect = [gdf1, gdf2]

        # Set up mock for create_derived_stac_item
        mock_derived_item = Mock(spec=Item)
        mock_create_derived_stac_item.return_value = mock_derived_item

        # Set up mock for create_stac_item_for_dataset
        mock_create_stac_item_for_dataset.return_value = mock_item1

        # Set up mock for STACReference
        mock_stac_ref = Mock(spec=STACReference)
        mock_stac_ref.item_id = "test-item-id"
        mock_stac_reference.new_from_timestamp.return_value = mock_stac_ref

        # Call the operation function with COLLECT geometry operation
        result = correlation_operation(
            dataset1_reference=self.dataset1_reference,
            dataset2_reference=self.dataset2_reference,
            distance=self.distance,
            dataset1_geo_column=self.dataset1_geo_column,
            dataset2_geo_column=self.dataset2_geo_column,
            workspace=self.mock_workspace,
            function_name=self.function_name,
            geometry_operation=GeometryOperationType.COLLECT,
        )

        # Verify the result contains expected text
        self.assertIn("correlated", result)
        self.assertIn("intersection", result)
        self.assertIn("'collect' geometry operation", result)

        # Verify the mocks were called
        self.assertEqual(mock_local_assets.call_count, 2)
        self.assertEqual(self.mock_workspace.read_geo_data_frame.call_count, 2)
        self.mock_workspace.write_geo_data_frame.assert_called_once()
        mock_create_derived_stac_item.assert_called_once()
        self.mock_workspace.create_item.assert_called_once()

    @patch("aws.osml.geoagents.spatial.correlation_operation.LocalAssets")
    @patch("aws.osml.geoagents.spatial.correlation_operation.create_derived_stac_item")
    @patch("aws.osml.geoagents.spatial.correlation_operation.create_stac_item_for_dataset")
    @patch("aws.osml.geoagents.spatial.correlation_operation.STACReference")
    def test_correlation_operation_union_geometry(
        self, mock_stac_reference, mock_create_stac_item_for_dataset, mock_create_derived_stac_item, mock_local_assets
    ):
        """Test intersection correlation with UNION geometry operation."""
        # Set up mocks for LocalAssets context manager
        mock_item1 = Mock(spec=Item)
        mock_item1.properties = {"title": "Test Dataset 1"}
        mock_local_asset_paths1 = {"asset1": Path("/tmp/asset1.parquet")}

        mock_item2 = Mock(spec=Item)
        mock_item2.properties = {"title": "Test Dataset 2"}
        mock_local_asset_paths2 = {"asset2": Path("/tmp/asset2.parquet")}

        # Configure the LocalAssets mock to return different values on each call
        mock_local_assets.return_value.__enter__.side_effect = [
            (mock_item1, mock_local_asset_paths1),
            (mock_item2, mock_local_asset_paths2),
        ]

        # Create mock GeoDataFrames with overlapping polygons
        polygon1 = shapely.Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
        polygon2 = shapely.Polygon([(0.5, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 1.5), (0.5, 0.5)])

        gdf1 = gpd.GeoDataFrame(geometry=[polygon1])
        gdf1.crs = "EPSG:4326"

        gdf2 = gpd.GeoDataFrame(geometry=[polygon2])
        gdf2.crs = "EPSG:4326"

        # Configure read_geo_data_frame to return different GeoDataFrames on each call
        self.mock_workspace.read_geo_data_frame.side_effect = [gdf1, gdf2]

        # Set up mock for create_derived_stac_item
        mock_derived_item = Mock(spec=Item)
        mock_create_derived_stac_item.return_value = mock_derived_item

        # Set up mock for create_stac_item_for_dataset
        mock_create_stac_item_for_dataset.return_value = mock_item1

        # Set up mock for STACReference
        mock_stac_ref = Mock(spec=STACReference)
        mock_stac_ref.item_id = "test-item-id"
        mock_stac_reference.new_from_timestamp.return_value = mock_stac_ref

        # Call the operation function with UNION geometry operation
        result = correlation_operation(
            dataset1_reference=self.dataset1_reference,
            dataset2_reference=self.dataset2_reference,
            distance=self.distance,
            dataset1_geo_column=self.dataset1_geo_column,
            dataset2_geo_column=self.dataset2_geo_column,
            workspace=self.mock_workspace,
            function_name=self.function_name,
            geometry_operation=GeometryOperationType.UNION,
        )

        # Verify the result contains expected text
        self.assertIn("correlated", result)
        self.assertIn("intersection", result)
        self.assertIn("'union' geometry operation", result)

        # Verify the mocks were called
        self.assertEqual(mock_local_assets.call_count, 2)
        self.assertEqual(self.mock_workspace.read_geo_data_frame.call_count, 2)
        self.mock_workspace.write_geo_data_frame.assert_called_once()
        mock_create_derived_stac_item.assert_called_once()
        self.mock_workspace.create_item.assert_called_once()

    @patch("aws.osml.geoagents.spatial.correlation_operation.LocalAssets")
    @patch("aws.osml.geoagents.spatial.correlation_operation.create_derived_stac_item")
    @patch("aws.osml.geoagents.spatial.correlation_operation.create_stac_item_for_dataset")
    @patch("aws.osml.geoagents.spatial.correlation_operation.STACReference")
    def test_correlation_operation_intersect_geometry(
        self, mock_stac_reference, mock_create_stac_item_for_dataset, mock_create_derived_stac_item, mock_local_assets
    ):
        """Test intersection correlation with INTERSECT geometry operation."""
        # Set up mocks for LocalAssets context manager
        mock_item1 = Mock(spec=Item)
        mock_item1.properties = {"title": "Test Dataset 1"}
        mock_local_asset_paths1 = {"asset1": Path("/tmp/asset1.parquet")}

        mock_item2 = Mock(spec=Item)
        mock_item2.properties = {"title": "Test Dataset 2"}
        mock_local_asset_paths2 = {"asset2": Path("/tmp/asset2.parquet")}

        # Configure the LocalAssets mock to return different values on each call
        mock_local_assets.return_value.__enter__.side_effect = [
            (mock_item1, mock_local_asset_paths1),
            (mock_item2, mock_local_asset_paths2),
        ]

        # Create mock GeoDataFrames with overlapping polygons
        polygon1 = shapely.Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
        polygon2 = shapely.Polygon([(0.5, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 1.5), (0.5, 0.5)])

        gdf1 = gpd.GeoDataFrame(geometry=[polygon1])
        gdf1.crs = "EPSG:4326"

        gdf2 = gpd.GeoDataFrame(geometry=[polygon2])
        gdf2.crs = "EPSG:4326"

        # Configure read_geo_data_frame to return different GeoDataFrames on each call
        self.mock_workspace.read_geo_data_frame.side_effect = [gdf1, gdf2]

        # Set up mock for create_derived_stac_item
        mock_derived_item = Mock(spec=Item)
        mock_create_derived_stac_item.return_value = mock_derived_item

        # Set up mock for create_stac_item_for_dataset
        mock_create_stac_item_for_dataset.return_value = mock_item1

        # Set up mock for STACReference
        mock_stac_ref = Mock(spec=STACReference)
        mock_stac_ref.item_id = "test-item-id"
        mock_stac_reference.new_from_timestamp.return_value = mock_stac_ref

        # Call the operation function with INTERSECT geometry operation
        result = correlation_operation(
            dataset1_reference=self.dataset1_reference,
            dataset2_reference=self.dataset2_reference,
            distance=self.distance,
            dataset1_geo_column=self.dataset1_geo_column,
            dataset2_geo_column=self.dataset2_geo_column,
            workspace=self.mock_workspace,
            function_name=self.function_name,
            geometry_operation=GeometryOperationType.INTERSECT,
        )

        # Verify the result contains expected text
        self.assertIn("correlated", result)
        self.assertIn("intersection", result)
        self.assertIn("'intersect' geometry operation", result)

        # Verify the mocks were called
        self.assertEqual(mock_local_assets.call_count, 2)
        self.assertEqual(self.mock_workspace.read_geo_data_frame.call_count, 2)
        self.mock_workspace.write_geo_data_frame.assert_called_once()
        mock_create_derived_stac_item.assert_called_once()
        self.mock_workspace.create_item.assert_called_once()

    @patch("aws.osml.geoagents.spatial.correlation_operation.LocalAssets")
    @patch("aws.osml.geoagents.spatial.correlation_operation.create_derived_stac_item")
    @patch("aws.osml.geoagents.spatial.correlation_operation.create_stac_item_for_dataset")
    @patch("aws.osml.geoagents.spatial.correlation_operation.STACReference")
    def test_correlation_operation_difference_geometry(
        self, mock_stac_reference, mock_create_stac_item_for_dataset, mock_create_derived_stac_item, mock_local_assets
    ):
        """Test intersection correlation with DIFFERENCE geometry operation."""
        # Set up mocks for LocalAssets context manager
        mock_item1 = Mock(spec=Item)
        mock_item1.properties = {"title": "Test Dataset 1"}
        mock_local_asset_paths1 = {"asset1": Path("/tmp/asset1.parquet")}

        mock_item2 = Mock(spec=Item)
        mock_item2.properties = {"title": "Test Dataset 2"}
        mock_local_asset_paths2 = {"asset2": Path("/tmp/asset2.parquet")}

        # Configure the LocalAssets mock to return different values on each call
        mock_local_assets.return_value.__enter__.side_effect = [
            (mock_item1, mock_local_asset_paths1),
            (mock_item2, mock_local_asset_paths2),
        ]

        # Create mock GeoDataFrames with overlapping polygons
        polygon1 = shapely.Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
        polygon2 = shapely.Polygon([(0.5, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 1.5), (0.5, 0.5)])

        gdf1 = gpd.GeoDataFrame(geometry=[polygon1])
        gdf1.crs = "EPSG:4326"

        gdf2 = gpd.GeoDataFrame(geometry=[polygon2])
        gdf2.crs = "EPSG:4326"

        # Configure read_geo_data_frame to return different GeoDataFrames on each call
        self.mock_workspace.read_geo_data_frame.side_effect = [gdf1, gdf2]

        # Set up mock for create_derived_stac_item
        mock_derived_item = Mock(spec=Item)
        mock_create_derived_stac_item.return_value = mock_derived_item

        # Set up mock for create_stac_item_for_dataset
        mock_create_stac_item_for_dataset.return_value = mock_item1

        # Set up mock for STACReference
        mock_stac_ref = Mock(spec=STACReference)
        mock_stac_ref.item_id = "test-item-id"
        mock_stac_reference.new_from_timestamp.return_value = mock_stac_ref

        # Call the operation function with DIFFERENCE geometry operation
        result = correlation_operation(
            dataset1_reference=self.dataset1_reference,
            dataset2_reference=self.dataset2_reference,
            distance=self.distance,
            dataset1_geo_column=self.dataset1_geo_column,
            dataset2_geo_column=self.dataset2_geo_column,
            workspace=self.mock_workspace,
            function_name=self.function_name,
            geometry_operation=GeometryOperationType.DIFFERENCE,
        )

        # Verify the result contains expected text
        self.assertIn("correlated", result)
        self.assertIn("intersection", result)
        self.assertIn("'difference' geometry operation", result)

        # Verify the mocks were called
        self.assertEqual(mock_local_assets.call_count, 2)
        self.assertEqual(self.mock_workspace.read_geo_data_frame.call_count, 2)
        self.mock_workspace.write_geo_data_frame.assert_called_once()
        mock_create_derived_stac_item.assert_called_once()
        self.mock_workspace.create_item.assert_called_once()


if __name__ == "__main__":
    unittest.main()
