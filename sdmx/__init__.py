import logging
from importlib.metadata import PackageNotFoundError, version

from sdmx.client import Client, Request, read_url
from sdmx.format.xml.common import install_schemas, validate_xml
from sdmx.reader import read_sdmx
from sdmx.rest import Resource
from sdmx.source import add_source, list_sources
from sdmx.writer import to_csv, to_pandas, to_xml

__all__ = [
    "Client",
    "Request",
    "Resource",
    "add_source",
    "install_schemas",
    "list_sources",
    "log",
    "read_sdmx",
    "read_url",
    "to_csv",
    "to_pandas",
    "to_xml",
    "validate_xml",
]


try:
    __version__ = version("sdmx1")
except PackageNotFoundError:  # pragma: no cover
    # Local copy or not installed with setuptools
    __version__ = "999"


#: Top-level logger.
#:
#: .. versionadded:: 0.4
log = logging.getLogger(__name__)
