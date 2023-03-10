"""SDMX-CSV reader stub."""
from sdmx.format import list_media_types
from sdmx.reader.base import BaseReader


class Reader(BaseReader):
    """Read SDMX-CSV."""

    media_types = list_media_types(base="csv")
    suffixes = [".csv"]

    def read_message(self, source, dsd=None):  # pragma: no cover
        raise NotImplementedError
