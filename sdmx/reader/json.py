"""SDMX-JSON v2.1 reader"""
import json
import logging
from typing import Mapping, MutableMapping

from dateutil.parser import isoparse

from sdmx.format import Version, list_media_types
from sdmx.message import DataMessage, Header
from sdmx.model import common
from sdmx.model import v21 as model
from sdmx.model.common import Concept
from sdmx.model.internationalstring import InternationalString
from sdmx.model.v21 import (
    ActionType,
    AllDimensions,
    AttributeValue,
    DataSet,
    Key,
    KeyValue,
    Observation,
    SeriesKey,
)
from sdmx.reader.base import BaseReader

log = logging.getLogger(__name__)


class Reader(BaseReader):
    """Read SDMX-JSON and expose it as instances from :mod:`sdmx.model`."""

    media_types = list_media_types(base="json", version=Version["1.0.0"])
    suffixes = [".json"]

    @classmethod
    def detect(cls, content):
        return content.startswith(b"{")

    # FIXME Reduce complexity from 17 → 13
    def read_message(self, source, dsd=None):  # noqa: C901
        # Initialize message instance
        msg = DataMessage()

        if dsd:  # pragma: no cover
            # Store explicit DSD, if any
            msg.dataflow.structure = dsd

        # Read JSON
        source.default_size = -1
        tree = json.load(source)

        # Read the header
        # TODO handle KeyError here
        try:
            # SDMX-JSON 1.0 (SDMX 2.1)
            elem = tree["header"]
        except KeyError:
            # SDMX-JSON 2.0 (SDMX 3.0.0)
            elem = tree["meta"]

        msg.header = Header(
            id=elem["id"],
            prepared=isoparse(elem["prepared"]),
            sender=_org(elem["sender"], cls=common.Agency),
        )

        # pre-fetch some structures for efficient use in series and obs
        try:
            # SDMX-JSON 1.0 (SDMX 2.1)
            structure = tree["structure"]
        except KeyError:
            # SDMX-JSON 2.0 (SDMX 3.0.0)
            structure = tree["data"]["structures"]

        # Read dimensions and values
        self._dim_level = dict()
        self._dim_values = dict()
        for level_name, level in structure["dimensions"].items():
            for elem in level:
                # Create the Dimension
                d = msg.structure.dimensions.getdefault(
                    id=elem["id"], order=elem.get("keyPosition", -1)
                )

                # Record the level it appears at
                self._dim_level[d] = level_name

                # Record values
                self._dim_values[d] = list()
                for value in elem.get("values", []):
                    self._dim_values[d].append(KeyValue(id=d.id, value=value["id"]))

        # Assign an order to an implicit dimension
        for d in msg.structure.dimensions:
            if d.order == -1:
                d.order = len(msg.structure.dimensions)

        # Determine the dimension at the observation level
        if all([level == "observation" for level in self._dim_level.values()]):
            dim_at_obs = AllDimensions
        else:
            dim_at_obs = [
                dim for dim, level in self._dim_level.items() if level == "observation"
            ]

        msg.observation_dimension = dim_at_obs

        # Read attributes and values
        self._attr_level = dict()
        self._attr_values = dict()
        for level_name, level in structure["attributes"].items():
            for attr in level:
                # Create a DataAttribute in the DSD
                da = msg.structure.attributes.getdefault(
                    id=attr["id"], concept_identity=Concept(name=attr["name"])
                )

                # Record its values
                values = []
                for v in attr.get("values", []):
                    values.append(
                        AttributeValue(
                            value=model.Code(**v) if "id" in v else v["name"],
                            value_for=da,
                        )
                    )

                # Handle https://github.com/khaeru/sdmx/issues/64: a DataAttribute with
                # no values cannot be referenced, and is assumed to be erroneously
                # included.
                if not len(values):
                    log.warning(f"No AttributeValues for attribute {repr(da)}; discard")

                    # Remove the DataAttribute
                    idx = msg.structure.attributes.components.index(da)
                    msg.structure.attributes.components.pop(idx)

                    continue

                self._attr_values[da] = values

                # Record the level it appears at
                self._attr_level[da] = level_name

        self.msg = msg

        # Make a SeriesKey for Observations in this DataSet
        ds_key = self._make_key("dataSet")

        # Read DataSets
        for ds in tree["dataSets"]:
            msg.data.append(self.read_dataset(ds, ds_key))

        return msg

    def read_dataset(self, root, ds_key):
        ds = DataSet(
            action=ActionType[root["action"].lower()],
            valid_from=root.get("validFrom", None),
        )

        # Process series
        for key_values, elem in root.get("series", {}).items():
            series_key = self._make_key("series", key_values, base=ds_key)
            series_key.attrib = self._make_attrs("series", root.get("attributes", []))
            ds.add_obs(self.read_obs(elem, series_key=series_key), series_key)

        # Process bare observations
        ds.add_obs(self.read_obs(root, base_key=ds_key))

        return ds

    def read_obs(self, root, series_key=None, base_key=None):
        for key, elem in root.get("observations", {}).items():
            value = elem.pop(0) if len(elem) else None
            o = Observation(
                series_key=series_key,
                dimension=self._make_key("observation", key, base=base_key),
                value=value,
                attached_attribute=self._make_attrs("observation", elem),
            )
            yield o

    def _make_key(self, level, value=None, base=None):
        """Convert a string observation key *value* to a Key or subclass.

        SDMXJSON observations have keys like '2' or '3:4', consisting of colon
        (':') separated indices. Each index refers to one of the values given
        in the DSD for an observation-level dimension.

        KeyValues from any *base* Key are copied, and the new values appended.
        *level* species whether a 'series' or 'observation' Key is returned.
        """
        # Instance of the proper class
        key = {"dataSet": Key, "series": SeriesKey, "observation": Key}[level]()

        if base:
            key.values.update(base.values)

        # Dimensions at the appropriate level
        dims = [d for d in self.msg.structure.dimensions if self._dim_level[d] == level]

        # Dimensions specified at the dataSet level have only one value, so
        # pre-fill this
        value = ":".join(["0"] * len(dims)) if value is None else value

        if len(value):
            # Iterate over key indices and the corresponding dimensions
            for index, dim in zip(map(int, value.split(":")), dims):
                # Look up the value and assign to the Key
                key[dim.id] = self._dim_values[dim][index]

        # Order the key
        return self.msg.structure.dimensions.order_key(key)

    def _make_attrs(self, level, values):
        """Convert integer attribute indices to an iterable of AttributeValues.

        'level' must be one of 'dataSet', 'series', or 'observation'.
        """
        attrs = [
            a for a in self.msg.structure.attributes if self._attr_level[a] == level
        ]
        result = {}
        for index, attr in zip(values, attrs):
            if index is None:
                continue
            av = self._attr_values[attr][index]
            result[av.value_for.id] = av
        return result


def _org(elem: MutableMapping, cls=common.Organisation) -> common.Organisation:
    try:
        elem["contact"] = list(map(_contact, elem.pop("contacts")))
    except KeyError:
        pass
    return cls(**maybe_parse_is(elem, "name"))


def _contact(elem: Mapping) -> common.Contact:
    data = depluralize(
        maybe_parse_is(elem, "department name role"),
        "email fax|faxe telephone uri x400",
    )
    if "id" in data:
        log.debug(f"Discard unsupported Contact(id={data.pop('id')!r})")
    try:
        data["org_unit"] = data.pop("department")
    except KeyError:  # pragma: no cover
        pass
    try:
        data["responsibility"] = data.pop("role")
    except KeyError:  # pragma: no cover
        pass
    return common.Contact(**data)


def depluralize(elem: Mapping, names: str) -> MutableMapping:
    """Map plural `names` in `elem` to singular.

    `names` is a whitespace-separated sequence of strings; each string is either the
    singular form and base for the plural form ("cat" → "cat" and "cats") or a pipe (|)
    separating the singular and plural base ("fox|foxe" → "fox", "foxes").
    """
    result = dict(elem)
    for name in names.split():
        info = name.split("|")
        try:
            result[info[0]] = result.pop(f"{info[-1]}s")
        except KeyError:  # pragma: no cover
            pass
    return result


def maybe_parse_is(elem: Mapping, names: str) -> Mapping:
    """Parse international string(s) with given `names` appearing on `elem`, if any."""
    result = dict(elem)
    for name in names.split():
        if name in result and f"{name}s" in result:
            result[name] = InternationalString(result.pop(f"{name}s"))
    return result
