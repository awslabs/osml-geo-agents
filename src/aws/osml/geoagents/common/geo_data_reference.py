#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import logging
from enum import Enum
from pathlib import Path
from typing import Union

import shapely

from .stac_reference import STACReference

logger = logging.getLogger(__name__)


class GeoDataReferenceType(Enum):
    """Enumeration of geospatial reference types."""

    WKT = "wkt"
    FILE_PATH = "file_path"
    S3_URL = "s3_url"
    STAC = "stac"


class GeoDataReference:
    """
    A universal identifier for geospatial data that can be resolved into a data file.

    Supports:
    - Well-Known Text (WKT) literals
    - Local file paths
    - S3 URLs
    - STAC references (stac:)

    This class provides a unified way to reference geospatial data from different sources.
    It only identifies the type of reference and stores the original reference string.
    The actual resolution of references to local files is handled by other classes.
    """

    def __init__(self, reference: str):
        """
        Initialize a GeoDataReference from a string.

        :param reference: The reference string (WKT, file path, S3 URL, or STAC reference)
        :raises ValueError: If the reference string is invalid or cannot be parsed
        """
        self.reference_string = reference
        self.reference_type = self._detect_reference_type(reference)
        self._validate_reference(reference)

    def _detect_reference_type(self, reference: str) -> GeoDataReferenceType:
        """
        Detect the type of geospatial reference.

        :param reference: The reference string
        :return: The detected reference type
        """
        if reference.startswith("stac:"):
            return GeoDataReferenceType.STAC
        elif reference.startswith("s3://"):
            return GeoDataReferenceType.S3_URL
        elif reference.upper().startswith(
            ("POINT", "LINESTRING", "POLYGON", "MULTIPOINT", "MULTILINESTRING", "MULTIPOLYGON", "GEOMETRYCOLLECTION")
        ):
            return GeoDataReferenceType.WKT
        else:
            # Assume it's a file path if it doesn't match other patterns
            return GeoDataReferenceType.FILE_PATH

    def _validate_reference(self, reference: str) -> None:
        """
        Validate that the reference string is valid for its detected type.

        :param reference: The reference string
        :raises ValueError: If the reference is invalid for its type
        """
        if self.reference_type == GeoDataReferenceType.WKT:
            try:
                shapely.from_wkt(reference)
            except Exception as e:
                logger.debug(f"Invalid WKT string: {reference}", exc_info=True)
                raise ValueError(f"Invalid WKT string: {e}")

        elif self.reference_type == GeoDataReferenceType.STAC:
            try:
                STACReference(reference)
            except ValueError as e:
                logger.debug(f"Invalid STAC reference: {reference}", exc_info=True)
                raise ValueError(f"Invalid STAC reference: {e}")

        elif self.reference_type == GeoDataReferenceType.S3_URL:
            if not reference.startswith("s3://"):
                raise ValueError("S3 URL must start with 's3://'")

            # Basic validation of S3 URL format
            parts = reference[5:].split("/", 1)
            if len(parts) < 2 or not parts[0]:
                raise ValueError("Invalid S3 URL format. Expected: s3://bucket/key")

    def is_wkt(self) -> bool:
        """
        Check if the reference is a WKT string.

        :return: True if the reference is a WKT string, False otherwise
        """
        return self.reference_type == GeoDataReferenceType.WKT

    def is_file_path(self) -> bool:
        """
        Check if the reference is a file path.

        :return: True if the reference is a file path, False otherwise
        """
        return self.reference_type == GeoDataReferenceType.FILE_PATH

    def is_s3_url(self) -> bool:
        """
        Check if the reference is an S3 URL.

        :return: True if the reference is an S3 URL, False otherwise
        """
        return self.reference_type == GeoDataReferenceType.S3_URL

    def is_stac_reference(self) -> bool:
        """
        Check if the reference is a STAC reference.

        :return: True if the reference is a STAC reference, False otherwise
        """
        return self.reference_type == GeoDataReferenceType.STAC

    @classmethod
    def from_wkt(cls, wkt: str) -> "GeoDataReference":
        """
        Create a GeoDataReference from a WKT string.

        :param wkt: WKT string
        :return: GeoDataReference object
        :raises ValueError: If the WKT string is invalid
        """
        return cls(wkt)

    @classmethod
    def from_file_path(cls, path: Union[str, Path]) -> "GeoDataReference":
        """
        Create a GeoDataReference from a file path.

        :param path: File path (string or Path object)
        :return: GeoDataReference object
        """
        return cls(str(path))

    @classmethod
    def from_s3_url(cls, url: str) -> "GeoDataReference":
        """
        Create a GeoDataReference from an S3 URL.

        :param url: S3 URL (s3://bucket/key)
        :return: GeoDataReference object
        :raises ValueError: If the URL is not a valid S3 URL
        """
        if not url.startswith("s3://"):
            raise ValueError("S3 URL must start with 's3://'")
        return cls(url)

    @classmethod
    def from_stac_reference(cls, stac_ref: Union[STACReference, str]) -> "GeoDataReference":
        """
        Create a GeoDataReference from a STAC reference.

        :param stac_ref: STACReference object or string
        :return: GeoDataReference object
        :raises ValueError: If the STAC reference is invalid
        """
        if isinstance(stac_ref, STACReference):
            return cls(str(stac_ref))
        return cls(stac_ref)

    def __str__(self) -> str:
        """Return the string representation of the reference."""
        return self.reference_string
