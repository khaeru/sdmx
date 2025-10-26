from dataclasses import dataclass

from sdmx.format.common import Format


@dataclass
class JSONFormat(Format):
    """Information about an SDMX-JSON format."""

    suffix = "json"


class JSON_v10(JSONFormat):
    version = "1.0"


class JSON_v20(JSONFormat):
    version = "2.0.0"


class JSON_v21(JSONFormat):
    version = "2.1.0"
