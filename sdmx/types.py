from typing import TypedDict

from pandas.tseries.offsets import (
    Day,
    Hour,
    Micro,
    Milli,
    Minute,
    MonthEnd,
    Nano,
    QuarterEnd,
    Second,
    Week,
    YearEnd,
)

from sdmx.convert.pandas import Attributes
from sdmx.format.csv.common import CSVFormatOptions
from sdmx.model.common import Agency

# See https://github.com/pandas-dev/pandas-stubs/pull/1394#issuecomment-3356958356
PeriodFrequency = (
    Day
    | Hour
    | Minute
    | Second
    | Milli
    | Micro
    | Nano
    | YearEnd
    | QuarterEnd
    | MonthEnd
    | Week
)


class VersionableArtefactArgs(TypedDict, total=False):
    version: str


class MaintainableArtefactArgs(VersionableArtefactArgs):
    maintainer: Agency


class ToCSVArgs(TypedDict, total=False):
    attributes: Attributes
    format_options: CSVFormatOptions
