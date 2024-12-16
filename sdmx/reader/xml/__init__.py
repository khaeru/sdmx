from importlib import import_module
from itertools import chain
from warnings import warn

from lxml import etree

from sdmx.format import list_media_types
from sdmx.reader.base import BaseReader

from .v21 import XMLParseError

__all__ = ["XMLParseError"]


class Reader(BaseReader):
    """Reader that detects and dispatches to either v21 or v30."""

    binary_content_startswith = b"<"
    media_types = list_media_types(base="xml")
    suffixes = [".xml"]

    @classmethod
    def detect(cls, content):
        warn(
            "Reader.detect(bytes); use Converter.handles() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return content.startswith(cls.binary_content_startswith)

    def convert(self, data, **kwargs):
        # Create an iterative parser
        events = etree.iterparse(data, events=("start", "end"))

        # Peek at the start event for the first tag
        event, element = next(events)

        # Determine the SDMX-ML version
        version = ""
        for url in element.nsmap.values():
            if "v3_0" in url:
                version = "v30"
                break
            elif "v2_1" in url:
                version = "v21"
                break
        assert version, "Cannot determine SDMX-ML version"

        # - Import and instantiate the reader for this version.
        # - Return the peeked (event, element) to the head of the events iterator.
        return (
            import_module(f"sdmx.reader.xml.{version}")
            .Reader()
            .convert(None, **kwargs, _events=chain([(event, element)], events))
        )
