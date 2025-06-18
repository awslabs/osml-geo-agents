#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from pathlib import Path

from aws.osml.geoagents.common import STAC_PROTOCOL, GeoDataReference, GeoDataReferenceType, STACReference


class TestGeoDataReference(unittest.TestCase):
    def test_wkt_reference(self):
        """Test initialization with WKT strings"""
        # Test with a valid WKT string
        wkt = "POINT(0 0)"
        ref = GeoDataReference(wkt)
        self.assertEqual(ref.reference_string, wkt)
        self.assertEqual(ref.reference_type, GeoDataReferenceType.WKT)
        self.assertTrue(ref.is_wkt())
        self.assertFalse(ref.is_file_path())
        self.assertFalse(ref.is_s3_url())
        self.assertFalse(ref.is_stac_reference())

        # Test with an invalid WKT string
        with self.assertRaises(ValueError):
            GeoDataReference("POINT(invalid)")

    def test_file_path_reference(self):
        """Test initialization with file paths"""
        # Test with a string path
        path_str = "/path/to/file.shp"
        ref = GeoDataReference(path_str)
        self.assertEqual(ref.reference_string, path_str)
        self.assertEqual(ref.reference_type, GeoDataReferenceType.FILE_PATH)
        self.assertTrue(ref.is_file_path())
        self.assertFalse(ref.is_wkt())
        self.assertFalse(ref.is_s3_url())
        self.assertFalse(ref.is_stac_reference())

        # Test with a Path object
        path_obj = Path("/path/to/file.shp")
        ref = GeoDataReference.from_file_path(path_obj)
        self.assertEqual(ref.reference_string, str(path_obj))
        self.assertEqual(ref.reference_type, GeoDataReferenceType.FILE_PATH)
        self.assertTrue(ref.is_file_path())

    def test_s3_url_reference(self):
        """Test initialization with S3 URLs"""
        # Test with a valid S3 URL
        s3_url = "s3://bucket/key/to/file.geojson"
        ref = GeoDataReference(s3_url)
        self.assertEqual(ref.reference_string, s3_url)
        self.assertEqual(ref.reference_type, GeoDataReferenceType.S3_URL)
        self.assertTrue(ref.is_s3_url())
        self.assertFalse(ref.is_wkt())
        self.assertFalse(ref.is_file_path())
        self.assertFalse(ref.is_stac_reference())

        # Test with an invalid S3 URL
        with self.assertRaises(ValueError):
            GeoDataReference("s3://")

        # Test with a non-S3 URL
        with self.assertRaises(ValueError):
            GeoDataReference.from_s3_url("http://example.com")

    def test_stac_reference(self):
        """Test initialization with STAC references"""
        # Test with a valid STAC reference string
        stac_ref_str = f"{STAC_PROTOCOL}ABC123"
        ref = GeoDataReference(stac_ref_str)
        self.assertEqual(ref.reference_string, stac_ref_str)
        self.assertEqual(ref.reference_type, GeoDataReferenceType.STAC)
        self.assertTrue(ref.is_stac_reference())
        self.assertFalse(ref.is_wkt())
        self.assertFalse(ref.is_file_path())
        self.assertFalse(ref.is_s3_url())

        # Test with a valid STAC reference object
        stac_ref_obj = STACReference(stac_ref_str)
        ref = GeoDataReference.from_stac_reference(stac_ref_obj)
        self.assertEqual(ref.reference_string, str(stac_ref_obj))
        self.assertEqual(ref.reference_type, GeoDataReferenceType.STAC)
        self.assertTrue(ref.is_stac_reference())

        # Test with an invalid STAC reference
        with self.assertRaises(ValueError):
            GeoDataReference("stac:")

    def test_from_methods(self):
        """Test the from_* class methods"""
        # Test from_wkt
        wkt = "POINT(1 1)"
        ref = GeoDataReference.from_wkt(wkt)
        self.assertEqual(ref.reference_string, wkt)
        self.assertTrue(ref.is_wkt())

        # Test from_file_path with string
        path_str = "/path/to/file.shp"
        ref = GeoDataReference.from_file_path(path_str)
        self.assertEqual(ref.reference_string, path_str)
        self.assertTrue(ref.is_file_path())

        # Test from_file_path with Path object
        path_obj = Path("/path/to/file.shp")
        ref = GeoDataReference.from_file_path(path_obj)
        self.assertEqual(ref.reference_string, str(path_obj))
        self.assertTrue(ref.is_file_path())

        # Test from_s3_url
        s3_url = "s3://bucket/key/to/file.geojson"
        ref = GeoDataReference.from_s3_url(s3_url)
        self.assertEqual(ref.reference_string, s3_url)
        self.assertTrue(ref.is_s3_url())

        # Test from_stac_reference with string
        stac_ref_str = f"{STAC_PROTOCOL}ABC123"
        ref = GeoDataReference.from_stac_reference(stac_ref_str)
        self.assertEqual(ref.reference_string, stac_ref_str)
        self.assertTrue(ref.is_stac_reference())

        # Test from_stac_reference with STACReference object
        stac_ref_obj = STACReference(stac_ref_str)
        ref = GeoDataReference.from_stac_reference(stac_ref_obj)
        self.assertEqual(ref.reference_string, str(stac_ref_obj))
        self.assertTrue(ref.is_stac_reference())

    def test_string_representation(self):
        """Test the string representation"""
        wkt = "POINT(0 0)"
        ref = GeoDataReference(wkt)
        self.assertEqual(str(ref), wkt)

        path_str = "/path/to/file.shp"
        ref = GeoDataReference(path_str)
        self.assertEqual(str(ref), path_str)

        s3_url = "s3://bucket/key/to/file.geojson"
        ref = GeoDataReference(s3_url)
        self.assertEqual(str(ref), s3_url)

        stac_ref_str = f"{STAC_PROTOCOL}ABC123"
        ref = GeoDataReference(stac_ref_str)
        self.assertEqual(str(ref), stac_ref_str)


if __name__ == "__main__":
    unittest.main()
