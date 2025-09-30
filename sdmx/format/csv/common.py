"""Information about SDMX-CSV file formats."""

import operator
from dataclasses import dataclass, fields, replace
from enum import Enum, Flag, auto
from functools import reduce

from sdmx.format.common import Format, FormatOptions


class Attributes(Flag):
    """Attributes to include."""

    #: No attributes.
    none = 0

    #: Attributes attached to each :class:`Observation <.BaseObservation>`.
    observation = auto()
    o = observation

    #: Attributes attached to any (0 or 1) :class:`~.SeriesKey` associated with each
    #: Observation.
    series_key = auto()
    s = series_key

    #: Attributes attached to any (0 or more) :class:`~.GroupKey` associated with each
    #: Observation.
    group_key = auto()
    g = group_key

    #: Attributes attached to the :class:`~.DataSet` containing the Observations.
    dataset = auto()
    d = dataset

    all = observation | series_key | group_key | dataset

    @classmethod
    def parse(cls, value: str) -> "Attributes":
        try:
            values = [Attributes.none] + [cls[v] for v in value.lower()]
        except KeyError as e:
            raise ValueError(f"{e.args[0]!r} is not a member of {cls}")
        return reduce(operator.or_, values)


class Labels(Enum):
    """SDMX-CSV 'labels' parameter."""

    #: Display only :attr:`IdentifiableArtefact.id`, for :class:`.Dimension` or
    #: :class:`.DataAttribute` in column headers and :class:`.Code` in data rows.
    id = auto()

    #: Display both the ID and the localized :attr:`NameableArtefact.name`.
    both = auto()

    #: Display only the localized name. Not present in SDMX-CSV 1.0
    name = auto()  # type: ignore [assignment]


class TimeFormat(Enum):
    """SDMX-CSV 'timeFormat' parameter."""

    #: Values for any dimension or attribute with ID ``TIME_PERIOD`` are displayed
    #: as recorded.
    original = auto()

    #: ``TIME_PERIOD`` values are converted to the most granular ISO 8601 representation
    #: taking into account the highest frequency of the data in the message and the
    #: moment in time when the lower-frequency values were collected.
    normalized = auto()


@dataclass
class CSVFormat(Format):
    """Information about an SDMX-CSV format."""

    suffix = "csv"


@dataclass
class CSVFormatOptions(FormatOptions):
    """SDMX-CSV format options.

    These options and default values are common to SDMX-CSV 1.0, 2.0.0, and 2.1.0.
    """

    format = CSVFormat

    #: Types of labels included.
    labels: Labels = Labels.id

    #: Time format.
    time_format: TimeFormat = TimeFormat.original

    def __post_init__(self) -> None:
        # Convert string arguments to enum members
        if isinstance(self.labels, str):
            self.labels = Labels[str(self.labels).lower()]
        if isinstance(self.time_format, str):
            self.time_format = TimeFormat[str(self.time_format).lower()]


def kwargs_to_format_options(kwargs: dict, cls: type["CSVFormatOptions"]) -> None:
    """Separate from `kwargs` any attributes of :class:`CSVFormatOptions`."""
    _fo = "format_options"
    # Either an existing instance of CSVFormatOptions or a subclass, or a new/default
    # instance
    existing = kwargs.pop(_fo, cls()) or cls()

    # Keys in `kwargs` that should be assigned to a FormatOptions instance
    keys = set(f.name for f in fields(existing)) & set(kwargs)
    replacements = {k: kwargs.pop(k) for k in keys}

    # Replace or set existing instance with `existing` + `replacements`
    kwargs[_fo] = replace(existing, **replacements)
