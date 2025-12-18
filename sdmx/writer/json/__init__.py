from typing import TYPE_CHECKING

from sdmx.format.json import JSON_v20, JSON_v21

if TYPE_CHECKING:
    from sdmx.message import DataMessage, StructureMessage


def to_json(obj: "DataMessage | StructureMessage", **kwargs) -> str:
    format = kwargs.get("format", JSON_v20)
    if format in (JSON_v20, JSON_v21):
        from . import v2

        return v2.JSONWriter(**kwargs).convert(obj)
    else:
        from . import v1

        return v1.JSONWriter(**kwargs).convert(obj)
