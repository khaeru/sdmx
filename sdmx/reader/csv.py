import csv
import logging
import re
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from itertools import zip_longest
from typing import TYPE_CHECKING, Literal, MutableSequence, Optional, Sequence, Union

import sdmx.message
from sdmx.format import list_media_types
from sdmx.model import common, v30
from sdmx.reader import base
from sdmx.reader.base import BaseReader

if TYPE_CHECKING:
    from typing import TypedDict

    import pandas

    from sdmx.model import v21

    class DataSetKwargs(TypedDict):
        described_by: Optional[common.BaseDataflow]
        structured_by: common.BaseDataStructureDefinition


log = logging.getLogger(__name__)


@dataclass
class Options:
    """SDMX-CSV 2.0.0 format options."""

    #: Types of labels included. Appears in the specification.
    labels: Literal["both", "id", "name"] = "id"

    #: Whether series, observation, or no keys are expressed in their own columns (in
    #: addition to dimension columns). Appears in the specification.
    key: Literal["both", "none", "obs", "series"] = "none"

    #: “Custom columns” detected by :meth:`.Reader.inspect_header`.
    custom_columns: list[bytes] = field(default_factory=list)

    #: CSV field delimiter.
    delimiter: str = ","

    #: SDMX-CSV “sub-field” delimiter.
    delimiter_sub: str = ""


class Reader(BaseReader):
    """Read SDMX-CSV."""

    # BaseReader attributes
    media_types = list_media_types(base="csv")
    suffixes = [".csv"]

    #: Handlers for individual fields in a CSV record. This collection has exactly the
    #: same number of handlers as columns in the `data` passed to :meth:`convert`.
    handlers: Sequence["Handler"]

    _dataflow: Optional["common.BaseDataflow"]
    _structure: Union["v21.DataStructureDefinition", "v30.DataStructure"]
    _observations: dict[tuple[str, str, str], list["common.BaseObservation"]]

    def __init__(self):
        self.options = Options()
        self.handlers = []
        self._dataflow = None
        self._structure = None
        self._observations = defaultdict(list)

    def convert(self, data, structure=None, *, delimiter: str = ",", **kwargs):
        """Read a message from `data`."""
        self.options.delimiter = delimiter

        if isinstance(structure, common.BaseDataflow):
            self._dataflow = structure
            self._structure = structure.structure
        else:
            self._dataflow = None
            self._structure = structure

        # Create a CSV reader
        lines = data.read().decode().splitlines()
        reader = csv.reader(lines, delimiter=self.options.delimiter)

        self.inspect_header(next(reader))

        # Parse remaining rows to observations
        for i, row in enumerate(reader):
            self.handle_row(row)

        # Create a data message
        self.message = sdmx.message.DataMessage(dataflow=self._dataflow)

        # Create 1 data set for each of the 4 ActionType values
        ds_kw: "DataSetKwargs" = dict(
            described_by=self._dataflow, structured_by=self._structure
        )
        for (*_, action), obs in self._observations.items():
            a = common.ActionType[
                {"A": "append", "D": "delete", "I": "information", "R": "replace"}[
                    action
                ]
            ]

            self.message.data.append(v30.DataSet(action=a, **ds_kw))
            self.message.data[-1].add_obs(obs)

        return self.message

    def handle_row(self, row: list[str]) -> None:
        """Handle a single CSV row."""
        obs = v30.Observation(
            dimension=v30.Key(),
            attached_attribute={"__TARGET": v30.AttributeValue(value=[])},
        )

        for h, v in zip_longest(self.handlers, row):
            h(obs, v)

        # Remove the "__TARGET" annotation and construct a key describing the data set
        # to which this observation belongs
        target = tuple(obs.attached_attribute.pop("__TARGET").value)

        self._observations[target].append(obs)

    def inspect_header(self, header: list[str]) -> None:  # noqa: C901  TODO Reduce complexity from 12 → ≤10
        """Inspect the SDMX-CSV header and determine the format :class:`.Options`.

        Raises
        ------
        ValueError
            if the data contain malformed SDMX-CSV 2.0.0.
        """
        handlers: MutableSequence[Optional["Handler"]] = [
            StoreTarget(allowable={"dataflow", "dataprovision", "datastructure"}),
            StoreTarget(),
        ] + ([None] * (len(header) - 2))

        # Columns in fixed order

        if match := re.fullmatch(r"STRUCTURE(\[(?P<delimiter_sub>.)\])?", header[0]):
            self.options.delimiter_sub = match.groupdict().get("delimeter_sub", None)
        else:
            raise ValueError(
                f"Invalid SDMX-CSV 2.0.0: {header[0]!r} in line 1, field 1; "
                "expected 'STRUCTURE' or 'STRUCTURE[…]'"
            )

        if not header[1] == "STRUCTURE_ID":
            raise ValueError(
                f"Invalid SDMX-CSV 2.0.0: {header[1]!r} in line 1, field 2; "
                "expected 'STRUCTURE_ID'"
            )

        i = 2
        if header[i] == "STRUCTURE_NAME":
            self.options.labels = "name"
            handlers[i] = Name()
            i += 1

        # Maybe a column "ACTION"
        if header[i] == "ACTION":
            handlers[i] = StoreTarget(allowable=set("ADIR"))
            i += 1

        if i < len(header) and header[i] == "SERIES_KEY":
            self.options.key = "series"
            handlers[i] = SeriesKey()
            i += 1

        if i < len(header) and header[i] == "OBS_KEY":
            handlers[i] = ObsKey()
            self.options.key = {"none": "obs", "series": "both"}.get(self.options.key)
            i += 1

        # From this point, columns may appear in any order

        inspected = set(range(i))

        for cls, components, multi_possible in (
            (KeyValue, self._structure.dimensions, False),
            (ObsValue, self._structure.measures, False),
            (AttributeValue, self._structure.attributes, True),
        ):
            for c in components:
                pattern = re.compile(
                    c.id + (r"(?P<multi>\[\])?" if multi_possible else "") + "(|: .*)"
                )
                matches = list(filter(None, map(pattern.fullmatch, header[i:])))
                if not len(matches):
                    log.warning(f"No column detected for {c!r}")
                    continue

                idx = header.index(matches[0].string)
                handlers[idx] = cls(c, multi="multi" in matches[0].groupdict())
                inspected.add(idx)

                if self.options.labels == "name":
                    handlers[idx + 1] = Name()
                    inspected.add(idx + 1)

        for i in set(range(len(header))) - inspected:
            h = header[i]
            handlers[i] = Custom(h)
            self.options.custom_columns.append(h)

        self.handlers = tuple(filter(None, handlers))
        assert len(self.handlers) == len(header)


class DataFrameConverter(base.Converter):
    @classmethod
    def handles(cls, data, kwargs) -> bool:
        import pandas as pd

        return isinstance(data, pd.DataFrame) and "structure" in kwargs

    def convert(
        self, data: "pandas.DataFrame", structure=None, **kwargs
    ) -> "sdmx.message.DataMessage":
        assert 0 == len(kwargs)

        # TEMPORARY Use a Reader instance
        r = Reader()
        r._dataflow = structure
        r._structure = structure.structure
        r.inspect_header(data.columns.to_list())

        # Parse remaining rows to observations
        for _, row in data.iterrows():
            r.handle_row(row.to_list())

        # Create a data message
        message = sdmx.message.DataMessage(dataflow=r._dataflow)

        # Create 1 data set for each of the 4 ActionType values
        ds_kw: "DataSetKwargs" = dict(
            described_by=r._dataflow, structured_by=r._structure
        )
        for (*_, action), obs in r._observations.items():
            a = common.ActionType[
                {"A": "append", "D": "delete", "I": "information", "R": "replace"}[
                    action
                ]
            ]

            message.data.append(v30.DataSet(action=a, **ds_kw))
            message.data[-1].add_obs(obs)

        return message


class Handler(ABC):
    """Base class for :attr:`.Reader.handlers`."""

    @abstractmethod
    def __call__(self, obs: "common.BaseObservation", value: str) -> None:
        """Handle the `value` in one field/record, and update the resulting `obs`.

        Subclasses **must** implement this method.
        """

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


class Name(Handler):
    """Handler for :py:`Options.labels == "name"` columns.

    Does nothing; the values are not stored.
    """

    def __call__(self, obs, value):
        pass


class NotHandled(Handler):
    """Handler that does nothing."""

    def __call__(self, obs, value):
        log.info(f"Not handled: {self.__class__.__name__}: {value}")


class StoreTarget(Handler):
    """Store `value` on a special :class:`.DataAttribute` with ID "__TARGET" on `obs`.

    Used for the STRUCTURE, STRUCTURE_ID, and ACTION columns.
    """

    def __init__(self, allowable: Optional[set[str]] = None):
        self.allowable = allowable

    def __call__(self, obs, value):
        assert value in self.allowable if self.allowable else True
        obs.attached_attribute["__TARGET"].value.append(value)


class SeriesKey(NotHandled):
    """ "SERIES_KEY" columns are currently not handled."""

    pass


class ObsKey(NotHandled):
    """ "OBS_KEY" columns are currently not handled."""

    pass


class KeyValue(Handler):
    """Handle a :class:`~.common.KeyValue` for one :class:`.Dimension`."""

    def __init__(self, dimension, **kwargs):
        self.dimension = dimension

    def __call__(self, obs, value):
        obs.dimension.values[self.dimension.id] = v30.KeyValue(
            id=self.dimension.id, value=value, value_for=self.dimension
        )


class ObsValue(Handler):
    """Handle the :attr:`Observation.value <.BaseObservation.value>.

    In line with :mod:`.model.v30`, multiple values (for data structures with multiple
    measures) are currently not handled.
    """

    def __init__(self, measure, **kwargs):
        self.measure = measure

    def __call__(self, obs, value):
        obs.value = value


class AttributeValue(Handler):
    """Handle a :class:`.v30.AttributeValue` for one :class:`.DataAttribute`.

    The attribute value is attached to the `obs`.
    """

    def __init__(self, attribute, multi: bool):
        self.attribute = attribute
        if multi:
            log.info(f"Column {attribute.id!r}: multiple values will not be unpacked")

    def __call__(self, obs, value):
        obs.attached_attribute[self.attribute.id] = v30.AttributeValue(
            value=value, value_for=self.attribute
        )


class Custom(Handler):
    """Handler for custom columns.

    Currently values are ignored.

    .. todo:: Store as :class:`.Annotation` or temporary attribute values on `obs`.
    """

    def __init__(self, header: str):
        log.info(f"Column {header!r} detected as custom and will not be stored")

    def __call__(self, obs, value):
        pass
