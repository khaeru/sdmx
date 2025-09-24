"""Common code for describing SDMX data formats."""

from typing import ClassVar


class Format:
    """Information about a SDMX data/file format.

    Any concrete subclass corresponds to a specific version of a data/file format
    defined in a specific version of the SDMX standards.
    """

    #: Format version.
    version: ClassVar[str]

    #: Preferred file name suffix.
    suffix: ClassVar[str]


class FormatOptions:
    """Options for an SDMX data/file format."""

    format: ClassVar[type[Format]]
