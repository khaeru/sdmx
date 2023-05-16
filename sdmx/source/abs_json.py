from . import Source as BaseSource
from .abs import Source as ABS


class Source(BaseSource):
    _id = "ABS_JSON"

    handle_response = ABS.handle_response
