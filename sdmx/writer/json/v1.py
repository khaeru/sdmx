from sdmx import message

from .base import BaseJSONWriter


class JSONWriter(BaseJSONWriter):
    pass


@JSONWriter.register
def _message(w: "JSONWriter", obj: message.Message):
    raise NotImplementedError("Write SDMX-JSON 1.0")
