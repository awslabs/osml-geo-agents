#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import secrets
from dataclasses import dataclass
from typing import Optional

# TODO: Need to consider setting a standard for these georefs. Do not reinvent the wheel.
#       Initial thought is to adopt URI syntax for these references. If we go that route
#       we will need to select a new custom protocol. "geo:" is already proposed / defined
#       by RFC 5870 but it doesn't appear to cover our needs. An alternative of "georef:"
#       is used here without doing any work to actually formalize the syntax. See:
#       https://en.wikipedia.org/wiki/Geo_URI_scheme
GEOREF_PROTOCOL = "georef:"


@dataclass
class Georeference:
    """
    Represents a georeference with an optional asset tag.

    Format: georef:<id>#<asset name>
    Example: georef:123ABC456D#rgb
    The #<asset name> portion is optional.
    """

    encoded_value: str

    def __post_init__(self):
        """Validates and parses the georeference string after initialization."""
        if not self.encoded_value.startswith(GEOREF_PROTOCOL):
            raise ValueError(f"Georeference must start with '{GEOREF_PROTOCOL}'")

        # Split into ID and asset tag parts
        parts = self.encoded_value.split("#", 1)

        # Validate there's an actual ID after the prefix
        if len(parts[0]) <= len(GEOREF_PROTOCOL):
            raise ValueError(f"Georeference must include an ID after '{GEOREF_PROTOCOL}'")

        self._item_id = parts[0][len(GEOREF_PROTOCOL):]   # fmt: skip
        self._asset_tag = parts[1] if len(parts) > 1 else None

        # Validate asset tag if present
        if self._asset_tag is not None and not self._asset_tag:
            raise ValueError("Asset tag cannot be empty if specified")

    @property
    def item_id(self) -> str:
        """Returns the item ID portion of the georeference."""
        return self._item_id

    @property
    def asset_tag(self) -> Optional[str]:
        """Returns the asset tag if present, None otherwise."""
        return self._asset_tag

    @classmethod
    def new_random(cls, asset_tag: Optional[str] = None) -> "Georeference":
        """
        Constructs a new georeference using a UUID as the item ID.

        :param asset_tag: an optional reference to a specific asset
        :return: the new UUID based georeference
        """
        random_id = str(secrets.token_hex(16))
        return Georeference.from_parts(random_id, asset_tag)

    @classmethod
    def from_parts(cls, item_id: str, asset_tag: Optional[str] = None) -> "Georeference":
        """
        Constructs a new georeference from a provided item ID and optional asset tag.

        :param item_id: the item ID
        :param asset_tag: an optional reference to a specific asset
        :return: the new georeference
        """
        encoded_value = f"{GEOREF_PROTOCOL}{item_id}"
        if asset_tag:
            encoded_value += f"#{asset_tag}"
        return cls(encoded_value)

    def __str__(self) -> str:
        """Returns the string representation of the georeference."""
        return self.encoded_value

    def __eq__(self, other: object) -> bool:
        """Implements equality comparison."""
        if not isinstance(other, Georeference):
            return NotImplemented
        return self.encoded_value == other.encoded_value
