"""SDMX-CSV 2.x formats."""

from dataclasses import dataclass, field
from enum import Enum, auto

from sdmx.format.csv.common import CSVFormat, CSVFormatOptions


class Keys(Enum):
    """SDMX-CSV 2.x 'keys' parameter."""

    #: No related columns.
    none = auto()

    #: Both :attr:`obs` and :attr:`series`.
    both = auto()

    #: Include ``OBS_KEY`` column with key values for all dimension(s).
    obs = auto()

    #: Include ``SERIES_KEY`` column with key values for all dimension(s) *except* the
    #: one(s) attached to each observation.
    series = auto()


class FORMAT(CSVFormat):
    version = "2.0.0"


@dataclass
class FormatOptions(CSVFormatOptions):
    """SDMX-CSV 2.x format options."""

    format = FORMAT

    #: SDMX-CSV 'keys' parameter.
    keys: Keys = Keys.none

    #: “Custom columns” detected by :meth:`.Reader.inspect_header`.
    custom_columns: list[bytes] = field(default_factory=list)

    #: CSV field delimiter.
    delimiter: str = ","

    #: SDMX-CSV “sub-field” delimiter.
    delimiter_sub: str = ""
