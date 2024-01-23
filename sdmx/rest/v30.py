from dataclasses import dataclass

from sdmx.rest.common import URL as BaseURL
from sdmx.rest.common import Resource


@dataclass
class URL(BaseURL):
    """Utility class to build SDMX 3.0 REST web service URLs."""

    def join(self) -> str:
        """Join the URL parts, returning a complete URL."""
        resource_id = "all" if self.resource_id is None else self.resource_id
        version = "+" if self.version is None else self.version

        parts = [self.source.url]

        if self.resource_type == Resource.data:
            parts.extend([self.resource_type.name, self.resource_id])
            if self.key:
                parts.append(self.key)
        else:
            parts.extend(
                [
                    "structure",
                    self.resource_type.name,
                    self.agency_id,
                    resource_id,
                    version.replace("latest", "+"),
                ]
            )

        assert None not in parts, parts

        return "/".join(parts)
