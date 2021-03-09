import logging

import pkg_resources

from sdmx.client import Client, Request, read_url
from sdmx.reader import read_sdmx
from sdmx.source import add_source, list_sources
from sdmx.util import Resource
from sdmx.writer import to_pandas, to_xml

__all__ = [
    "Client",
    "Request",
    "Resource",
    "add_source",
    "list_sources",
    "log",
    "read_sdmx",
    "read_url",
    "to_pandas",
    "to_xml",
]


try:
    __version__ = pkg_resources.get_distribution("sdmx1").version
except Exception:
    # Local copy or not installed with setuptools
    __version__ = "999"


#: Top-level logger.
#:
#: .. versionadded:: 0.4
log = logging.getLogger(__name__)
