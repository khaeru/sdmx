import json
from typing import Any

from sdmx import message

from .base import BaseJSONWriter


class JSONWriter(BaseJSONWriter):
    pass


@JSONWriter.register
def _data_message(w: "JSONWriter", obj: message.DataMessage):
    result = {"meta": w.convert(obj.header)}
    return json.dumps(result)


@JSONWriter.register
def _error_message(w: "JSONWriter", obj: message.ErrorMessage):
    result = {"meta": w.convert(obj.header)}
    return json.dumps(result)


@JSONWriter.register
def _metadata_message(w: "JSONWriter", obj: message.MetadataMessage):
    result = {"meta": w.convert(obj.header)}
    return json.dumps(result)


@JSONWriter.register
def _structure_message(w: "JSONWriter", obj: message.StructureMessage):
    result = {"meta": w.convert(obj.header)}
    return json.dumps(result)


@JSONWriter.register
def _header(w: "JSONWriter", obj: message.Header):
    result: dict[str, Any] = {"test": obj.test}
    if obj.id:
        result.update(id=obj.id)

    return result
