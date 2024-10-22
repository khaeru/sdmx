import csv
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from itertools import zip_longest
from typing import TYPE_CHECKING, Literal, MutableSequence, Optional, Sequence, Union

import sdmx.message
from sdmx.format import list_media_types
from sdmx.model import common, v30
from sdmx.reader.base import BaseReader

if TYPE_CHECKING:
    from typing import TypedDict

    from sdmx.model import v21

    class DataSetKwargs(TypedDict):
        described_by: Optional[common.BaseDataflow]
        structured_by: common.BaseDataStructureDefinition


log = logging.getLogger(__name__)


@dataclass
class Options:
    # Defined in the spec
    labels: Literal["both", "id", "name"] = "id"
    key: Literal["both", "none", "obs", "series"] = "none"

    # Others
    custom_columns: list[bytes] = field(default_factory=list)
    delimiter: str = ","
    delimiter_sub: str = ""


class Reader(BaseReader):
    """Read SDMX-CSV."""

    # BaseReader attributes
    media_types = list_media_types(base="csv")
    suffixes = [".csv"]

    dataflow: Optional["common.BaseDataflow"]
    structure: Union["v21.DataStructureDefinition", "v30.DataStructure"]
    handlers: Sequence["Handler"]
    observations: dict[tuple[str, str, str], list["common.BaseObservation"]]

    def __init__(self):
        self.options = Options()
        self.handlers = []

    def read_message(self, source, structure=None, *, delimiter: str = ",", **kwargs):
        self.options.delimiter = delimiter

        if isinstance(structure, common.BaseDataflow):
            self.dataflow = structure
            self.structure = structure.structure
        else:
            self.dataflow = None
            self.structure = structure

        self.observations = defaultdict(list)

        # Create a CSV reader
        lines = source.read().decode().splitlines()
        reader = csv.reader(lines, delimiter=self.options.delimiter)

        self.inspect_header(next(reader))

        # Parse remaining rows to observations
        for i, row in enumerate(reader):
            self.handle_row(row)

        # Create a data message
        self.message = sdmx.message.DataMessage(dataflow=self.dataflow)

        # Create 1 data set for each of the 4 ActionType values
        ds_kw: "DataSetKwargs" = dict(
            described_by=self.dataflow, structured_by=self.structure
        )
        for (*_, action), obs in self.observations.items():
            a = common.ActionType[
                {"A": "append", "D": "delete", "I": "information", "R": "replace"}[
                    action
                ]
            ]

            self.message.data.append(v30.DataSet(action=a, **ds_kw))
            self.message.data[-1].add_obs(obs)

        return self.message

    def handle_row(self, row: list[str]):
        obs = v30.Observation(
            dimension=v30.Key(),
            attached_attribute={"__TARGET": v30.AttributeValue(value=[])},
        )

        for h, v in zip_longest(self.handlers, row):
            h(obs, v)

        target = tuple(obs.attached_attribute.pop("__TARGET").value)

        self.observations[target].append(obs)

    def inspect_header(self, header: list[str]) -> None:  # noqa: C901  TODO Reduce complexity from 12 → ≤10
        handlers: MutableSequence[Optional["Handler"]] = [
            StoreTarget(allowable={"dataflow", "dataprovision", "datastructure"}),
            StoreTarget(),
        ] + ([None] * (len(header) - 2))

        # Columns in fixed order

        if match := re.fullmatch(r"STRUCTURE(\[(?P<delimiter_sub>.)\])?", header[0]):
            self.options.delimiter_sub = match.groupdict().get("delimeter_sub", None)
        else:
            raise ValueError("Invalid SDMX-CSV")

        if not header[1] == "STRUCTURE_ID":
            raise ValueError("Invalid SDMX-CSV")

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
            (KeyValue, self.structure.dimensions, False),
            (ObsValue, self.structure.measures, False),
            (AttributeValue, self.structure.attributes, True),
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


class Handler:
    def __call__(self, obs: "common.BaseObservation", value: str) -> None:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


class Name(Handler):
    """Handler for Options.labels == "name".

    Does nothing; the values are not stored.
    """

    def __call__(self, obs, value):
        pass


class NotHandled(Handler):
    def __call__(self, obs, value):
        log.info(f"Not handled: {self.__class__.__name__}: {value}")


class StoreTarget(Handler):
    def __init__(self, allowable: Optional[set[str]] = None):
        self.allowable = allowable

    def __call__(self, obs, value):
        assert value in self.allowable if self.allowable else True
        obs.attached_attribute["__TARGET"].value.append(value)


class SeriesKey(NotHandled):
    pass


class ObsKey(NotHandled):
    pass


class KeyValue(Handler):
    def __init__(self, dimension, **kwargs):
        self.dimension = dimension

    def __call__(self, obs, value):
        obs.dimension.values[self.dimension.id] = v30.KeyValue(
            id=self.dimension.id, value=value, value_for=self.dimension
        )


class ObsValue(Handler):
    def __init__(self, measure, **kwargs):
        self.measure = measure

    def __call__(self, obs, value):
        obs.value = value


class AttributeValue(Handler):
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

    .. todo:: Store as :class:`.Annotation`.
    """

    def __init__(self, header: str):
        log.info(f"Column {header!r} detected as custom and will not be stored")

    def __call__(self, obs, value):
        pass
