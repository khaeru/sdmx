from dataclasses import dataclass

from sdmx.rest.common import URL as BaseURL


@dataclass
class URL(BaseURL):
    """Utility class to build SDMX 2.1 REST web service URLs.

    See also
    --------
    https://github.com/sdmx-twg/sdmx-rest/blob/v1.5.0/v2_1/ws/rest/src/sdmx-rest.yaml
    """

    def join(self) -> str:
        """Join the URL parts, returning a complete URL."""
        resource_id = "all" if self.resource_id is None else self.resource_id
        version = "latest" if self.version is None else self.version

        parts = [self.source.url, self.resource_type.name]

        if self.resource_type in self._resource_types_with_key:
            parts.append(self.resource_id)
            if self.key:
                parts.append(self.key)
        else:
            parts.extend([self.agency_id, resource_id, version])

        assert None not in parts, parts

        return "/".join(parts)
