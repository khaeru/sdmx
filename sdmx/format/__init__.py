import logging
from dataclasses import InitVar, dataclass, field
from enum import Enum, IntFlag
from functools import lru_cache
from typing import List, Literal, Optional, Union

from sdmx.util import parse_content_type

log = logging.getLogger(__name__)

#: Flag values for information about :class:`MediaType`:
#:
#: - ``data``: :obj:`True` if this format contains (meta)data. :obj:`False` if it
#:   contains (meta)data **structures**.
#: - ``meta``: :obj:`True` if this format contains metadata (or metadata structures).
#:   :obj:`False` otherwise.
#: - ``ss``: :obj:`True` if this format contains data that is structure-specific. This
#:   distinction is only relevant before SDMX 3.0.
#: - ``ts``: :obj:`True` if this format contains time-series data. This distinction is
#:   only relevant before SDMX 3.0.
Flag = IntFlag("Flag", "data meta ss ts")
f = Flag

#: SDMX standard versions. In this enumeration, the strings "3.0.0" and "3.0" evaluate
#: to the same member.
Version = Enum(
    "Version",
    {"1.0.0": 1, "2.0.0": 2, "2.1": 2.1, "3.0.0": 3, "3.0": 3, "unknown": None},
)


@dataclass(frozen=True)
class MediaType:
    """Structure of elements in :data:`MEDIA_TYPES`.

    The :func:`str` of a MediaType is generally of the form:

    ``application/vnd.sdmx.{label}+{base};version={version}``

    …unless :attr:`full` is provided, in which case label and base are ignored.
    """

    #: Distinguishing part of the media type.
    label: str

    #: The base media type or file format.
    base: Literal["csv", "json", "xml"]

    #: Format version.
    version: Version = field(init=False)
    _version: InitVar[Union[str, Version]]

    flags: Flag = Flag(0)

    #: Specify the full media type string.
    full: Optional[str] = None

    def __post_init__(self, _version):
        self.__dict__["version"] = Version[_version]

    def __repr__(self):
        """Full media type string."""
        return (
            self.full or f"application/vnd.sdmx.{self.label}+{self.base}"
        ) + f"; version={self.version.name}"

    @lru_cache()
    def match(self, value: str, strict: bool = False) -> bool:
        """:obj:`True` if `value` matches the current MediaType."""
        other = parse_content_type(value)
        other[1].pop("charset", None)
        this = parse_content_type(repr(self))

        if strict:
            return this == other
        else:
            result = this[0] == other[0]
            if result and this[1] != other[1]:
                log.debug(f"Match {this[0]} with params {other[1]}; expected {this[1]}")
            return result

    @property
    def is_data(self) -> bool:
        return bool(self.flags & Flag.data)

    @property
    def is_meta(self) -> bool:
        return bool(self.flags & Flag.meta)

    @property
    def is_structure_specific(self) -> bool:
        return bool(self.flags & Flag.ss)

    @property
    def is_time_series(self) -> bool:
        return bool(self.flags & Flag.ts)


#: SDMX formats. Each record is an instance of :class:`Format`.
MEDIA_TYPES = [
    # SDMX-ML
    # Version 2.1
    MediaType("generic", "xml", "2.1", f.data),
    MediaType("genericdata", "xml", "2.1", f.data),
    MediaType("genericmetadata", "xml", "2.1", f.data | f.meta),
    MediaType("generictimeseriesdata", "xml", "2.1", f.data | f.ts),
    MediaType("schema", "xml", "2.1", f.meta),
    MediaType("structure", "xml", "2.1"),
    MediaType("structurespecificdata", "xml", "2.1", f.data | f.ss),
    MediaType("structurespecificmetadata", "xml", "2.1", f.data | f.meta | f.ss),
    MediaType("structurespecifictimeseriesdata", "xml", "2.1", f.data | f.ss | f.ts),
    # Non-standard: returned by e.g. BIS, IMF, INSEE, LSD, NB, SGR, UNICEF
    MediaType("", "xml", "2.1", full="application/xml"),
    # Non-standard
    MediaType("", "xml", "2.1", full="text/xml"),
    # Version 3.0.0
    MediaType("data", "xml", "3.0.0", f.data),
    MediaType("structure", "xml", "3.0.0"),
    MediaType("metadata", "xml", "2.0.0", f.data),
    #
    # SDMX-JSON
    # Version 1.0.0
    MediaType("data", "json", "1.0.0", f.data),
    # Version 2.0.0
    MediaType("data", "json", "2.0.0", f.data),
    MediaType("structure", "json", "1.0.0"),
    MediaType("structure", "json", "2.0.0"),
    MediaType("metadata", "json", "2.0.0", f.data | f.meta),
    # Non-standard
    MediaType("draft-sdmx-json", "json", "1.0.0", f.data),
    # Non-standard; returned by e.g. NBB, STAT_EE
    MediaType("", "json", "1.0.0", f.data, full="draft-sdmx-json"),
    # Non-standard
    MediaType("", "json", "1.0.0", f.data, full="text/json"),
    #
    # SDMX-CSV
    # Version 1.0.0
    MediaType("data", "csv", "1.0.0", f.data),
    # Version 2.0.0
    MediaType("metadata", "csv", "2.0.0", f.data),
]


def list_media_types(**filters) -> List[MediaType]:
    """Return the string for each item in :data:`MEDIA_TYPES` matching `filters`."""
    result = []
    for mt in MEDIA_TYPES:
        if not all(getattr(mt, field) == value for field, value in filters.items()):
            continue
        result.append(mt)
    return result
