from sdmx.format import list_media_types
from sdmx.reader.base import BaseReader


class Reader(BaseReader):
    """Stub (incomplete) implementation of a SDMX-CSV reader."""

    media_types = list_media_types(base="csv")
    suffixes = [".csv"]

    def read_message(self, source, dsd=None):  # pragma: no cover
        """Not implemented."""
        raise NotImplementedError
