#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import datetime
import secrets
from dataclasses import dataclass
from typing import Optional

import numpy as np

# TODO: Need to consider setting a standard for these STAC references. Do not reinvent the wheel.
#       Initial thought is to adopt URI syntax for these references. If we go that route
#       we will need to select a new custom protocol. "stac:" is used here to represent
#       SpatioTemporal Asset Catalog references.
STAC_PROTOCOL = "stac:"


@dataclass
class STACReference:
    """
    Represents a STAC (SpatioTemporal Asset Catalog) reference with optional collections and asset tag.

    Format: stac:<collection1>/<collection2>/.../<id>#<asset name>
    Examples:
      - stac:123ABC456D#rgb
      - stac:foo/bar/123ABC456D#rgb

    The collections and #<asset name> portions are optional.
    """

    encoded_value: str

    def __post_init__(self):
        """Validates and parses the STAC reference string after initialization."""
        if not self.encoded_value:
            raise ValueError("STAC reference cannot be empty")

        if not isinstance(self.encoded_value, str):
            raise ValueError("STAC reference must be a string")

        if not self.encoded_value.startswith(STAC_PROTOCOL):
            raise ValueError(f"STAC reference must start with '{STAC_PROTOCOL}'")

        # Split into ID and asset tag parts
        parts = self.encoded_value.split("#", 1)

        # Validate there's an actual ID after the prefix
        if len(parts[0]) <= len(STAC_PROTOCOL):
            raise ValueError(f"STAC reference must include an ID after '{STAC_PROTOCOL}'")

        # Extract the path part (everything between protocol and asset tag)
        path_part = parts[0][len(STAC_PROTOCOL):]  # fmt: skip

        # Split path into collections and item_id
        path_components = path_part.split("/")

        # The last component is the item_id, everything before are collections
        self._item_id = path_components[-1]
        self._collections = path_components[:-1] if len(path_components) > 1 else []

        self._asset_tag = parts[1] if len(parts) > 1 else None

        # Validate asset tag if present
        if self._asset_tag is not None and not self._asset_tag:
            raise ValueError("Asset tag cannot be empty if specified")

    @property
    def item_id(self) -> str:
        """Returns the item ID portion of the STAC reference."""
        return self._item_id

    @property
    def collections(self) -> list[str]:
        """Returns the list of collection names in the STAC reference."""
        return self._collections

    @property
    def asset_tag(self) -> Optional[str]:
        """Returns the asset tag if present, None otherwise."""
        return self._asset_tag

    @classmethod
    def new_random(cls, asset_tag: Optional[str] = None, collections: Optional[list[str]] = None) -> "STACReference":
        """
        Constructs a new STAC reference using a UUID as the item ID.

        :param asset_tag: an optional reference to a specific asset
        :param collections: an optional list of collection names
        :return: the new UUID based STAC reference
        """
        random_id = str(secrets.token_hex(16))
        return STACReference.from_parts(random_id, asset_tag, collections)

    @classmethod
    def new_from_timestamp(
        cls,
        asset_tag: Optional[str] = None,
        prefix: Optional[str] = None,
        collections: Optional[list[str]] = None,
    ) -> "STACReference":
        """
        Constructs a new STAC reference using the current UTC timestamp encoded as a base36
        string as the item ID. The intent is to provide a short ID that will be unique within
        a session. A timestamp rounded to milliseconds and converted to base36 will be an
        8 character string that should be relatively unique within the context of a normal
        chat session.

        This approach should not be used when the ID needs to be globally unique or in cases
        where the system will rapidly generate a series of IDs in parallel. In those situations
        use the new_random() function which creates a longer reference based on a UUID.

        :param asset_tag: an optional reference to a specific asset
        :param prefix: an optional string to prepend to the item id
        :param collections: an optional list of collection names
        :return: the new timestamp-based STAC reference
        """

        current_time = datetime.datetime.now(datetime.timezone.utc)
        timestamp_int = int(current_time.timestamp() * 1000)
        base36_id = np.base_repr(timestamp_int, 36)

        if prefix:
            base36_id = f"{prefix}-{base36_id}"

        return cls.from_parts(base36_id, asset_tag, collections)

    @classmethod
    def from_parts(
        cls,
        item_id: str,
        asset_tag: Optional[str] = None,
        collections: Optional[list[str]] = None,
    ) -> "STACReference":
        """
        Constructs a new STAC reference from a provided item ID, optional asset tag, and optional collections.

        :param item_id: the item ID
        :param asset_tag: an optional reference to a specific asset
        :param collections: an optional list of collection names
        :return: the new STAC reference
        """
        path_parts = []

        # Add collections if provided
        if collections:
            path_parts.extend(collections)

        # Add item_id
        path_parts.append(item_id)

        # Join with '/' separator
        path = "/".join(path_parts)

        encoded_value = f"{STAC_PROTOCOL}{path}"
        if asset_tag:
            encoded_value += f"#{asset_tag}"
        return cls(encoded_value)

    def __str__(self) -> str:
        """Returns the string representation of the STAC reference."""
        return self.encoded_value

    def __eq__(self, other: object) -> bool:
        """Implements equality comparison."""
        if not isinstance(other, STACReference):
            return NotImplemented
        return self.encoded_value == other.encoded_value
