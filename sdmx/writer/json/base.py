from typing import TYPE_CHECKING

from sdmx.convert.common import DispatchConverter

if TYPE_CHECKING:
    from sdmx.format.json import JSONFormat


class BaseJSONWriter(DispatchConverter):
    def __init__(self, format: "JSONFormat") -> None:
        pass
