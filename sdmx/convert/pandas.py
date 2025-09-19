"""Convert :mod:`sdmx.message`/:mod:`.model` objects to :mod:`pandas` objects."""

import operator
from dataclasses import dataclass, field
from enum import Flag, auto
from functools import reduce
from itertools import chain
from typing import TYPE_CHECKING, Any, Hashable, Optional, Union

import numpy as np
import pandas as pd

from sdmx import message, urn
from sdmx.dictlike import DictLike
from sdmx.format import csv
from sdmx.format.csv.common import CSVFormat, Labels, TimeFormat
from sdmx.model import common, v21
from sdmx.model.internationalstring import DEFAULT_LOCALE

from .common import DispatchConverter

if TYPE_CHECKING:
    from sdmx.format.csv.common import CSVFormatOptions
    from sdmx.model.common import BaseDataStructureDefinition, Item
    from sdmx.model.v21 import ContentConstraint

_HAS_PANDAS_2 = pd.__version__.split(".")[0] >= "2"

#: TODO Retrieve this info from the StructureMessage class.
ALL_CONTENTS = {
    "category_scheme",
    "codelist",
    "concept_scheme",
    "constraint",
    "dataflow",
    "structure",
    "organisation_scheme",
}


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


@dataclass
class PandasConverter(DispatchConverter):
    #: SDMX-CSV format options.
    format_options: "CSVFormatOptions"

    format: Optional["CSVFormat"] = None

    #: Attributes to include.
    attributes: Attributes = Attributes.none

    #: If given, only Observations included by the *constraint* are returned.
    constraint: Optional["ContentConstraint"] = None

    dsd: Optional["BaseDataStructureDefinition"] = None

    #: str or :class:`numpy.dtype` or None
    #:
    #: Datatype for values. If None, do not return the values of a series. In this case,
    #: `attributes` must be something other than :attr:`Attributes.none`, so that some
    #: attribute is returned.
    dtype: Any = np.float64

    #: :any:`True` to convert datetime.
    datetime: bool = False
    #: ID of a dimension to convert to :class:`pandas.DatetimeIndex`.
    datetime_dimension_id: Optional[str] = None
    #: Frequency for conversion to :class:`pandas.PeriodIndex`.
    datetime_freq: Any = False
    #: Axis on which to place a time dimension. Default 0 (index).
    datetime_axis: int = 0

    #: include : iterable of str or str, optional
    #:     One or more of the attributes of the StructureMessage ('category_scheme',
    #:     'codelist', etc.) to transform.
    include: set[str] = field(default_factory=lambda: set(ALL_CONTENTS))

    locale: str = DEFAULT_LOCALE

    #: Default return type for :func:`write_dataset` and similar methods. Either
    #: 'compat' or 'rows'. See the ref:`HOWTO <howto-rtype>`.
    rtype: str = "rows"

    _data_message: Optional[message.DataMessage] = None

    def handle_datetime_option(self) -> None:
        """Handle alternate forms of :attr:`datetime`.

        If given, return a DataFrame with a :class:`~pandas.DatetimeIndex` or
        :class:`~pandas.PeriodIndex` as the index and all other dimensions as columns.
        Valid `datetime` values include:

        - :class:`bool`: if :obj:`True`, determine the time dimension automatically by
          detecting a :class:`~.TimeDimension`.
        - :class:`str`: ID of the time dimension.
        - :class:`~.Dimension`: the matching Dimension is the time dimension.
        - :class:`dict`: advanced behaviour. Keys may include:

           - **dim** (:class:`~.Dimension` or :class:`str`): the time dimension or its
             ID.
           - **axis** (`{0 or 'index', 1 or 'columns'}`): axis on which to place the time
             dimension (default: 0).
           - **freq** (:obj:`True` or :class:`str` or :class:`~.Dimension`): produce
             :class:`pandas.PeriodIndex`. If :class:`str`, the ID of a Dimension
             containing a frequency specification. If a Dimension, the specified
             dimension is used for the frequency specification.

             Any Dimension used for the frequency specification is does not appear in the
             returned DataFrame.
        """
        value = self.datetime
        if isinstance(value, bool):
            pass
        elif isinstance(value, str):
            self.datetime_dimension_id = value
            self.datetime = True
        elif isinstance(value, common.DimensionComponent):
            self.datetime_dimension_id = value.id
            self.datetime = True
        elif isinstance(value, dict):
            self.datetime = True
            # Unpack a dict of 'advanced' arguments
            self.datetime_axis = value.pop("axis", 0)
            self.datetime_dimension_id = value.pop("dim", None)
            self.datetime_freq = value.pop("freq", False)
            if len(value):
                raise ValueError(f"Unexpected datetime={tuple(sorted(value))!r}")
        else:
            raise TypeError(f"PandasConverter(…, datetime={type(value)})")

    def __post_init__(self) -> None:
        """Transform and validate arguments."""
        if self.format_options.labels not in {Labels.id}:
            raise NotImplementedError(
                f"convert to SDMX-CSV with labels={self.format_options.labels}"
            )

        if self.format_options.time_format not in {TimeFormat.original}:
            raise NotImplementedError(
                f"convert to SDMX-CSV with time_format={self.format_options.time_format}"
            )

        # Handle arguments
        self.handle_datetime_option()

        if isinstance(self.include, str):
            self.include = set([self.include])
        # Silently discard invalid names
        self.include &= ALL_CONTENTS

        # Validate attributes argument
        if isinstance(self.attributes, str):
            self.attributes = Attributes.parse(self.attributes)

        if (
            self.rtype == "compat"
            and self._data_message
            and self._data_message.observation_dimension is not common.AllDimensions
        ):
            # Cannot return attributes in this case
            self.attributes = Attributes.none


def to_pandas(obj, **kwargs):
    """Convert an SDMX *obj* to :mod:`pandas` object(s).

    See :ref:`sdmx.convert.pandas <convert-pandas>`.
    """
    from sdmx.format.csv.v1 import FormatOptions

    kwargs.setdefault("format_options", FormatOptions())

    return PandasConverter(**kwargs).convert(obj)


# Functions for Python containers
@PandasConverter.register
def _list(c: "PandasConverter", obj: list):
    """Convert a :class:`list` of SDMX objects."""
    if isinstance(obj[0], common.BaseObservation):
        return convert_dataset(c, v21.DataSet(obs=obj))
    elif isinstance(obj[0], common.BaseDataSet) and len(obj) == 1:
        return c.convert(obj[0])
    elif isinstance(obj[0], common.SeriesKey):
        return convert_serieskeys(obj)
    else:
        return [c.convert(item) for item in obj]


@PandasConverter.register
def _dict(c: "PandasConverter", obj: dict):
    """Convert mappings."""
    result = {k: c.convert(v) for k, v in obj.items()}

    result_type = set(type(v) for v in result.values())

    if result_type <= {pd.Series, pd.DataFrame}:
        if (
            len(set(map(lambda s: s.index.name, result.values()))) == 1
            and len(result) > 1
        ):
            # Can safely concatenate these to a pd.MultiIndex'd Series.
            return pd.concat(result)
        else:
            # The individual pd.Series are indexed by different dimensions; do not
            # concatenate
            return DictLike(result)
    elif result_type == {str}:
        return pd.Series(result)
    elif result_type < {dict, DictLike}:
        return result
    elif result_type == set():
        # No results
        return pd.Series()
    else:
        raise ValueError(result_type)


@PandasConverter.register
def _set(c: "PandasConverter", obj: set):
    """Convert :class:`set` recursively."""
    return {c.convert(o) for o in obj}


# Functions for message classes
@PandasConverter.register
def convert_datamessage(c: "PandasConverter", obj: message.DataMessage):
    """Convert :class:`.DataMessage`.

    Parameters
    ----------
    rtype : 'compat' or 'rows', optional
        Data type to return; default :data:`.DEFAULT_RTYPE`. See the
        :ref:`HOWTO <howto-rtype>`.
    kwargs :
        Passed to :func:`convert_dataset` for each data set.

    Returns
    -------
    :class:`pandas.Series` or :class:`pandas.DataFrame`
        if `obj` has only one data set.
    list of (:class:`pandas.Series` or :class:`pandas.DataFrame`)
        if `obj` has more than one data set.
    """
    # Store a reference to `obj`
    c._data_message = obj
    # Use the specified structure of the message
    assert obj.dataflow
    c.dsd = obj.dataflow.structure

    if len(obj.data) == 1:
        return c.convert(obj.data[0])
    else:
        return [c.convert(ds) for ds in obj.data]


@PandasConverter.register
def convert_structuremessage(c: "PandasConverter", obj: message.StructureMessage):
    """Convert :class:`.StructureMessage`.

    Returns
    -------
    .DictLike
        Keys are StructureMessage attributes; values are pandas objects.
    """
    attrs = sorted(c.include)
    result: DictLike[str, Union[pd.Series, pd.DataFrame]] = DictLike()
    for a in attrs:
        dl = c.convert(getattr(obj, a))
        if len(dl):
            # Only add non-empty elements
            result[a] = dl

    return result


# Functions for model classes


@PandasConverter.register
def _c(c: "PandasConverter", obj: common.Component):
    """Convert :class:`.Component`."""
    assert obj.concept_identity
    return str(obj.concept_identity.id)


@PandasConverter.register
def _cc(c: "PandasConverter", obj: v21.ContentConstraint):
    """Convert :class:`.ContentConstraint`."""
    return {i: c.convert(cr) for i, cr in enumerate(obj.data_content_region)}


@PandasConverter.register
def _cr(c: "PandasConverter", obj: common.CubeRegion):
    """Convert :class:`.CubeRegion`."""
    result: DictLike[str, pd.Series] = DictLike()
    for dim, ms in obj.member.items():
        result[dim.id] = pd.Series([c.convert(sv) for sv in ms.values], name=dim.id)
    return result


@PandasConverter.register
def _rp(c: "PandasConverter", obj: v21.RangePeriod):
    """Convert :class:`.RangePeriod`."""
    return f"{obj.start.period}–{obj.end.period}"


@PandasConverter.register
def convert_dataset(c: "PandasConverter", obj: common.BaseDataSet):  # noqa: C901
    """Convert :class:`~.DataSet`.

    See the :ref:`walkthrough <datetime>` for examples of using the `datetime` argument.

    Parameters
    ----------
    obj : :class:`~.DataSet` or iterable of :class:`Observation <.BaseObservation>`

    Returns
    -------
    :class:`pandas.DataFrame`
        - if :attr:`~PandasConverter.attributes` is not ``''``, a data frame with one
          row per Observation, ``value`` as the first column, and additional columns for
          each attribute;
        - if `datetime` is given, various layouts as described above; or
        - if `_rtype` (passed from :func:`convert_datamessage`) is 'compat', various
          layouts as described in the :ref:`HOWTO <howto-rtype>`.
    :class:`pandas.Series` with :class:`pandas.MultiIndex`
        Otherwise.
    """
    # FIXME Reduce complexity from 13 to ≤10

    common: dict[str, Any] = {}  # Common values for every row

    if c.format is csv.v1.FORMAT:
        # SDMX-CSV 1.0 'DATAFLOW' column
        if obj.described_by is None:
            raise ValueError(f"No associated data flow definition for {obj}")
        dfd_urn = urn.make(obj.described_by).split("=", maxsplit=1)[1]
        common.update(DATAFLOW=dfd_urn)
    elif c.format and c.format is csv.v2.FORMAT:
        raise NotImplementedError(f"convert DataSet to SDMX-CSV {c.format.version}")

    # Add the attributes of the data set (SDMX 2.1 only)
    if (c.attributes & Attributes.dataset) and isinstance(obj, v21.DataSet):
        common.update(obj.attrib)

    # Iterate on observations
    data: dict[Hashable, dict[str, Any]] = {}
    for observation in obj.obs:
        # Check that the Observation is within the constraint, if any
        key = observation.key.order()
        if c.constraint and key not in c.constraint:
            continue

        # Add value and attributes
        row = common.copy()
        if c.dtype:
            row["value"] = observation.value
        if c.attributes:
            # Add the combined attributes from observation, series- and group keys
            row.update(observation.attrib)

        data[tuple(map(str, key.get_values()))] = row

    result: Union[pd.Series, pd.DataFrame] = pd.DataFrame.from_dict(
        data, orient="index"
    )

    if len(result):
        result.index.names = observation.key.order().values.keys()
        if c.dtype:
            try:
                result["value"] = result["value"].astype(c.dtype)
            except ValueError:
                # Attempt to handle locales in which LC_NUMERIC.decimal_point is ","
                # TODO Make this more robust by inferring and changing locale settings
                result["value"] = result["value"].str.replace(",", ".").astype(c.dtype)
            if not c.attributes:
                result = result["value"]

    # Reshape for compatibility with v0.9
    result = _dataset_compat(c, result)
    # Handle the datetime argument, if any
    return _maybe_convert_datetime(c, result, obj=obj)


def _dataset_compat(c: "PandasConverter", df) -> pd.DataFrame:
    """Helper for :meth:`.convert_dataset` 0.9 compatibility."""
    if c.rtype != "compat":
        return df  # Do nothing

    # FIXME Reword old comment: Remove compatibility arguments from kwargs
    assert c._data_message is not None
    obs_dim = c._data_message.observation_dimension
    if isinstance(obs_dim, list) and len(obs_dim) == 1:
        # Unwrap a length-1 list
        obs_dim = obs_dim[0]

    if obs_dim in (common.AllDimensions, None):
        pass  # Do nothing
    elif isinstance(obs_dim, common.TimeDimension):
        # Don't modify *df*; only change arguments so that _maybe_convert_datetime
        # performs the desired changes
        if c.datetime is False or c.datetime is True:
            # Either datetime is not given, or True without specifying a dimension;
            # overwrite
            c.datetime_dimension_id = obs_dim.id
        elif isinstance(c.datetime, dict):
            # Dict argument; ensure the 'dim' key is the same as obs_dim
            if c.datetime_dimension_id != obs_dim.id:
                raise ValueError(
                    f"datetime={c.datetime} conflicts with rtype='compat' and {obs_dim} "
                    "at observation level"
                )
        else:
            assert c.datetime == obs_dim, (c.datetime, obs_dim)
    elif isinstance(obs_dim, common.DimensionComponent):
        # Pivot all levels except the observation dimension
        df = df.unstack([n for n in df.index.names if n != obs_dim.id])
    else:
        # E.g. some JSON messages have two dimensions at the observation level;
        # behaviour is unspecified here, so do nothing.
        pass

    return df


def _maybe_convert_datetime(  # noqa: C901
    c: "PandasConverter", df: "pd.DataFrame", obj
) -> "pd.DataFrame":
    """Helper for :func:`convert_dataset` to handle datetime indices.

    Parameters
    ----------
    c :
        Converter. :attr:`.PandasConverter.datetime`, :attr:`.PandasConverter.dsd` and
        related attributes affect the conversion.
    df :
    obj :
        From the `obj` argument to :meth:`convert_dataset`.
    """
    # TODO Simplify this method to reduce its McCabe complexity from 18 to <=10
    if c.datetime is False:
        return df

    # Unpack argument values
    dim_id = c.datetime_dimension_id  # ID of a Dimension containing datetimes
    axis = c.datetime_axis
    freq = c.datetime_freq  # FIXME This is either a frequency spec or dimension ID

    def _get(kind: str):
        """Return an appropriate list of dimensions or attributes."""
        if len(getattr(obj.structured_by, kind).components):
            return getattr(obj.structured_by, kind).components
        elif c.dsd:
            return getattr(c.dsd, kind).components
        else:
            return []

    # Determine time dimension
    if not dim_id:
        for dim in filter(
            lambda d: isinstance(d, common.TimeDimension), _get("dimensions")
        ):
            dim_id = dim
            break
    if not dim_id:
        raise ValueError(f"no TimeDimension in {_get('dimensions')}")

    # Unstack all but the time dimension and convert
    other_dims = list(filter(lambda d: d != dim_id, df.index.names))
    # FIXME Satisfy mypy in the following
    df = df.unstack(other_dims)  # type: ignore
    # Only provide format in pandas >= 2.0.0
    kw = dict(format="mixed") if _HAS_PANDAS_2 else {}
    # FIXME Address mypy errors here
    df.index = pd.to_datetime(df.index, **kw)  # type: ignore

    # Convert to a PeriodIndex with a particular frequency
    if freq:
        try:
            # A frequency string recognized by pandas.PeriodDtype
            if isinstance(freq, str):
                freq = pd.PeriodDtype(freq=freq).freq
        except ValueError:
            # ID of a Dimension; Attribute; or column of `df`
            result = None
            for component in chain(
                _get("dimensions"),
                _get("attributes"),
                map(lambda id: common.Dimension(id=str(id)), df.columns.names),
            ):
                if component.id == freq:
                    freq = result = component
                    break

            if not result:
                raise ValueError(freq)

        if isinstance(freq, common.Dimension):
            # Retrieve Dimension values from pd.MultiIndex level
            level = freq.id
            assert isinstance(df.columns, pd.MultiIndex)
            i = df.columns.names.index(level)
            values = set(df.columns.levels[i])

            if len(values) > 1:
                raise ValueError(
                    f"cannot convert to PeriodIndex with non-unique freq={sorted(values)}"
                )

            # Store the unique value
            freq = values.pop()

            # Remove the index level
            df.columns = df.columns.droplevel(i)
        elif isinstance(freq, common.DataAttribute):
            raise NotImplementedError

        assert isinstance(df.index, pd.DatetimeIndex)
        df.index = df.index.to_period(freq=freq)

    if axis in {1, "columns"}:
        # Change axis
        df = df.transpose()

    return df


@PandasConverter.register
def _dd(c: "PandasConverter", obj: common.DimensionDescriptor):
    """Convert :class:`.DimensionDescriptor`.

    The collection of :attr:`.DimensionDescriptor.components` is converted.
    """
    return c.convert(obj.components)


@PandasConverter.register
def convert_itemscheme(c: "PandasConverter", obj: common.ItemScheme):
    """Convert :class:`.ItemScheme`.

    Parameters
    ----------
    locale : str, optional
        Locale for names to return.

    Returns
    -------
    pandas.Series or pandas.DataFrame
    """
    items = {}
    seen: set["Item"] = set()

    def add_item(item):
        """Recursive helper for adding items."""
        # Track seen items
        if item in seen:
            return
        else:
            seen.add(item)

        items[item.id] = dict(
            # Localized name
            name=item.name.localized_default(c.locale),
            # Parent ID
            parent=item.parent.id if isinstance(item.parent, item.__class__) else "",
        )

        # Add this item's children, recursively
        for child in item.child:
            add_item(child)

    for item in obj:
        add_item(item)

    # Convert to DataFrame
    result: Union[pd.DataFrame, pd.Series] = pd.DataFrame.from_dict(
        items,
        orient="index",
        dtype=object,  # type: ignore [arg-type]
    ).rename_axis(obj.id, axis="index")

    if len(result) and not result["parent"].str.len().any():
        # 'parent' column is empty; convert to pd.Series and rename
        result = result["name"].rename(obj.name.localized_default(c.locale))

    return result


@PandasConverter.register
def _mv(c: "PandasConverter", obj: common.BaseMemberValue):
    return obj.value


@PandasConverter.register
def _mds(c: "PandasConverter", obj: common.BaseMetadataSet):
    raise NotImplementedError(f"convert {type(obj).__name__} to pandas")


@PandasConverter.register
def _na(c: "PandasConverter", obj: common.NameableArtefact):
    """Fallback for NameableArtefact: only its name."""
    return str(obj.name)


def convert_serieskeys(obj: list["common.SeriesKey"]) -> pd.DataFrame:
    result = []
    for sk in obj:
        result.append({dim: kv.value for dim, kv in sk.order().values.items()})
    # TODO perhaps return as a pd.MultiIndex if that is more useful
    return pd.DataFrame(result)
