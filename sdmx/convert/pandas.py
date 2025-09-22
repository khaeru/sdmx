"""Convert :mod:`sdmx.message`/:mod:`.model` objects to :mod:`pandas` objects."""

import operator
from collections.abc import Iterable, Sequence
from dataclasses import InitVar, dataclass, field
from enum import Flag, auto
from functools import reduce
from itertools import chain
from typing import TYPE_CHECKING, Any, Optional, Union
from warnings import warn

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
    from typing import TypedDict

    from pandas.core.dtypes.base import ExtensionDtype
    from pandas.tseries.offsets import DateOffset

    from sdmx.format.csv.common import CSVFormatOptions
    from sdmx.model.common import BaseObservation, Item
    from sdmx.model.v21 import ContentConstraint

    class ToDatetimeKeywords(TypedDict, total=False):
        format: str


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
class ColumnSpec:
    """Information about columns and index levels for conversion."""

    #: Initial columns.
    start: list[str] = field(default_factory=list)
    #: Columns related to observation keys.
    key: list[str] = field(default_factory=list)
    #: Columns related to observation measures.
    measure: list[str] = field(default_factory=list)
    #: Columns related to observation-attached attributes.
    obs_attrib: list[str] = field(default_factory=list)
    #: Final columns.
    end: list[str] = field(default_factory=list)

    #: Fixed values for some columns.
    assign: dict[str, str] = field(default_factory=dict)

    #: Columns to be set as index levels, then unstacked.
    unstack: list[str] = field(default_factory=list)

    @property
    def obs(self) -> list[str]:
        return self.key + self.measure + self.obs_attrib

    @property
    def full(self) -> list[str]:
        return self.start + self.obs + self.end

    def add_obs_attrib(self, values: Iterable[str]) -> None:
        if missing := set(values) - set(self.obs_attrib):
            self.obs_attrib.extend(missing)


@dataclass
class PandasConverter(DispatchConverter):
    #: SDMX-CSV format options.
    format_options: "CSVFormatOptions"

    #: If given, DataMessage and contents are converted to valid SDMX-CSV of this
    #: format, with the given :attr:`format_options`.
    format: Optional["CSVFormat"] = None

    #: Attributes to include.
    attributes: Attributes = Attributes.none

    #: If given, only Observations included by the *constraint* are returned.
    constraint: Optional["ContentConstraint"] = None

    #: Datatype for observation values. If :any:`None`, data values remain
    #: :class:`object`/:class:`str`.
    dtype: Union[type["np.generic"], type["ExtensionDtype"], str, None] = np.float64

    #: ID of a dimension to convert to :class:`pandas.DatetimeIndex`.
    datetime_dimension: Optional["common.DimensionComponent"] = None
    #: Frequency for conversion to :class:`pandas.PeriodIndex`.
    datetime_freq: Optional["DateOffset"] = None
    #: Axis on which to place a time dimension.
    datetime_axis: Union[int, str] = -1

    #: include : iterable of str or str, optional
    #:     One or more of the attributes of the StructureMessage ('category_scheme',
    #:     'codelist', etc.) to transform.
    include: set[str] = field(default_factory=lambda: set(ALL_CONTENTS))

    locale: str = DEFAULT_LOCALE

    #: :any:`True` to convert datetime.
    datetime: InitVar = None
    #: Default return type for :func:`write_dataset` and similar methods. Either
    #: 'compat' or 'rows'. See the ref:`HOWTO <howto-rtype>`.
    rtype: InitVar[str] = ""

    _context: dict[Union[str, type], Any] = field(
        default_factory=lambda: dict(compat=False)
    )

    def get_components(self, kind) -> list["common.Component"]:
        """Return an appropriate list of dimensions or attributes."""
        if ds := self._context.get(common.BaseDataSet, None):
            return getattr(ds.structured_by, kind).components
        elif dsd := self._context.get(
            common.BaseDataStructureDefinition
        ):  # pragma: no cover
            return getattr(dsd, kind).components
        else:  # pragma: no cover
            return []

    def handle_compat(self) -> None:
        """Analyse and alter settings for deprecated :py:`rtype=compat` argument."""
        if not self._context["compat"]:
            return

        # "Dimension at observation level" from the overall message
        obs_dim = self._context[message.DataMessage].observation_dimension

        if isinstance(obs_dim, common.TimeDimension):
            # Set datetime_dimension; convert_datetime() does the rest
            self.datetime_dimension = obs_dim
        elif isinstance(obs_dim, common.DimensionComponent):
            # Explicitly mark the other dimensions to be unstacked
            self._context[ColumnSpec].unstack = [
                d.id for d in self.get_components("dimensions") if d.id != obs_dim.id
            ]

    def handle_datetime(self, value: Any) -> None:
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
        if value is None:
            return

        warn(
            f"datetime={value} argument of type {type(value)}. Instead, set other "
            "datetime_… fields directly.",
            DeprecationWarning,
            stacklevel=2,
        )

        if isinstance(value, (str, common.DimensionComponent)):
            self.datetime_dimension = value  # type: ignore [assignment]
        elif isinstance(value, dict):
            # Unpack a dict of 'advanced' arguments
            self.datetime_axis = value.pop("axis", self.datetime_axis)
            self.datetime_dimension = value.pop("dim", self.datetime_dimension)
            self.datetime_freq = value.pop("freq", self.datetime_freq)
            if len(value):
                raise ValueError(f"Unexpected datetime={tuple(sorted(value))!r}")
        elif isinstance(value, bool):
            self.datetime_axis = 0 if value else -1
        else:
            raise TypeError(f"PandasConverter(…, datetime={type(value)})")

    def __post_init__(self, datetime: Any, rtype: Optional[str]) -> None:
        """Transform and validate arguments."""
        # Raise on unsupported arguments
        fo = self.format_options
        if self.format and self.format is csv.v2.FORMAT:
            raise NotImplementedError(
                f"convert DataSet to SDMX-CSV {self.format.version}"
            )
        elif fo.labels not in {Labels.id}:
            raise NotImplementedError(f"convert to SDMX-CSV with labels={fo.labels}")
        elif fo.time_format not in {TimeFormat.original}:
            raise NotImplementedError(
                f"convert to SDMX-CSV with time_format={fo.time_format}"
            )

        # Handle deprecated arguments
        self.handle_datetime(datetime)
        if rtype:
            warn(
                f"rtype={rtype!r} argument to to_pandas()/PandasConverter.",
                DeprecationWarning,
                stacklevel=2,
            )
            self._context["compat"] = rtype == "compat"

        # Convert other arguments to types expected by other code
        if isinstance(self.attributes, str):
            self.attributes = Attributes.parse(self.attributes)

        if isinstance(self.datetime_dimension, str):
            self.datetime_dimension = common.DimensionComponent(
                id=self.datetime_dimension
            )

        if isinstance(self.datetime_freq, str):
            try:
                # A frequency string recognized by pandas.PeriodDtype
                self.datetime_freq = pd.PeriodDtype(freq=self.datetime_freq).freq
            except ValueError:
                self.datetime_freq = common.Component(id=self.datetime_freq)

        if isinstance(self.include, str):
            self.include = set([self.include])
        # Silently discard invalid names
        self.include &= ALL_CONTENTS


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
    member_type = type(obj[0]) if len(obj) else object
    if issubclass(member_type, common.BaseDataSet) and 1 == len(obj):
        # Unpack a single data set
        return c.convert(obj[0])
    elif issubclass(member_type, common.BaseObservation):
        # Wrap a bare list of observations in DataSet
        return convert_dataset(c, v21.DataSet(obs=obj))
    elif issubclass(member_type, common.SeriesKey):
        # Return as pd.DataFrame instead of list
        return pd.DataFrame([c.convert(item) for item in obj])
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
        # Includes result_type == {}, i.e. no results
        return result
    else:  # pragma: no cover
        raise RuntimeError(f"Recursive conversion of {obj} returned {result_type}")


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
    # Update the context
    c._context[message.DataMessage] = obj
    # Use the specified structure of the message
    assert obj.dataflow
    c._context[common.BaseDataStructureDefinition] = obj.dataflow.structure

    # Convert list of data set objects
    result = c.convert(obj.data)

    c._context.pop(common.BaseDataStructureDefinition)
    c._context.pop(message.DataMessage)

    return result


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
def convert_dataset(c: "PandasConverter", obj: common.BaseDataSet):
    """Convert :class:`~.DataSet`.

    See the :ref:`walkthrough <datetime>` for examples of using the `datetime` argument.

        Parameters
        ----------
        obj : :class:`~.DataSet` or iterable of :class:`Observation <.BaseObservation>`

        Returns
        -------
        :class:`pandas.DataFrame`
            - if :attr:`~PandasConverter.attributes` is not ``''``, a data frame with one
              row per Observation, ``value`` as the first column, and additional columns
              for each attribute;
            - if `datetime` is given, various layouts as described above; or
            - if `_rtype` (passed from :func:`convert_datamessage`) is 'compat', various
              layouts as described in the :ref:`HOWTO <howto-rtype>`.
        :class:`pandas.Series` with :class:`pandas.MultiIndex`
            Otherwise.
    """
    # Sets of columns
    columns = c._context[ColumnSpec] = ColumnSpec()
    c._context[common.BaseDataSet] = obj

    if c.format is csv.v1.FORMAT:
        if obj.described_by is None:
            raise ValueError(f"No associated data flow definition for {obj}")

        # SDMX-CSV 1.0 'DATAFLOW' column
        dfd_urn = urn.make(obj.described_by)
        columns.start.append("DATAFLOW")
        columns.assign.update(DATAFLOW=dfd_urn.partition("=")[2])

    c.handle_compat()

    # Add the attributes of the data set (SDMX 2.1 only)
    if (c.attributes & Attributes.dataset) and isinstance(obj, v21.DataSet):
        columns.end.extend(obj.attrib.keys())
        columns.assign.update(obj.attrib)

    # Peek at first observation to determine column names
    try:
        obs0 = obj.obs[0]
    except IndexError:  # pragma: no cover
        return pd.DataFrame()
    columns.key.extend(obs0.key.order().values.keys())
    columns.measure.append("OBS_VALUE")
    if c.attributes:
        columns.obs_attrib.extend(obs0.attrib)

    def convert_obs(obs: "BaseObservation") -> Sequence[Union[str, None]]:
        """Convert a single Observation to pd.Series."""
        key = obs.key.order()
        if c.constraint and key not in c.constraint:
            # Emit an empty row to be dropped
            row: Sequence[Union[str, None]] = [None] * len(columns.obs)
        else:
            row = list(map(str, key.get_values())) + [
                None if obs.value is None else str(obs.value)
            ]
            if c.attributes:
                # Add the combined attributes from observation, series- and group keys
                row.extend(obs.attrib.values())
                columns.add_obs_attrib(obs.attrib)

        return row

    # - Apply convert_obs() to every obs → iterable of list.
    # - Create a pd.DataFrame.
    # - Drop empty rows (not in constraint).
    # - Set column names.
    # - Assign common values for all rows.
    # - Set column order.
    # - (Possibly) apply PandasConverter.dtype.
    # - (Possibly) convert certain columns to datetime.
    # - (Possibly) reshape.
    result = (
        pd.DataFrame(map(convert_obs, obj.obs))
        .dropna(how="all")
        .set_axis(columns.obs, axis=1)  # NB This must come after DataFrame(map(…))
        .assign(**columns.assign)
        .pipe(_apply_dtype, c)
        .pipe(_convert_datetime, c)
        .pipe(_reshape, c)
        .pipe(_to_periodindex, c)
    )

    c._context.pop(common.BaseDataSet)
    c._context.pop(ColumnSpec)

    return result


def _apply_dtype(df: "pd.DataFrame", c: "PandasConverter") -> "pd.DataFrame":
    """Apply `dtype` to 0 or more `columns`."""
    if c.dtype is None:
        return df

    # Create a mapping to apply `dtype` to multiple columns
    measure_cols = c._context[ColumnSpec].measure
    dtypes = {col: c.dtype for col in measure_cols}

    try:
        return df.astype(dtypes)
    except ValueError:
        # Attempt to handle locales in which LC_NUMERIC.decimal_point is ","
        # TODO Make this more robust by inferring and changing locale settings
        assign_kw = {col: df[col].str.replace(",", ".") for col in measure_cols}
        return df.assign(**assign_kw).astype(dtypes)


def _convert_datetime(df: "pd.DataFrame", c: "PandasConverter") -> "pd.DataFrame":
    """Possibly convert a column to a pandas datetime dtype."""
    if c.datetime_dimension is c.datetime_freq is None and c.datetime_axis == -1:
        return df

    # Identify a time dimension
    dims = c.get_components("dimensions")
    try:
        dim = c.datetime_dimension or next(
            filter(lambda d: isinstance(d, common.TimeDimension), dims)
        )
    except StopIteration:
        raise ValueError(f"no TimeDimension in {dims}")

    # Record index columns to be unstacked
    columns: "ColumnSpec" = c._context[ColumnSpec]
    columns.unstack = columns.unstack or list(
        map(str, filter(lambda d: d.id != dim.id, dims))
    )

    # Keyword args to pd.to_datetime(): only provide format= for pandas >=2.0.0
    dt_kw: "ToDatetimeKeywords" = dict(format="mixed") if _HAS_PANDAS_2 else {}

    # Convert the given column to a pandas datetime dtype
    return df.assign(**{dim.id: pd.to_datetime(df[dim.id], **dt_kw)})


def _ensure_multiindex(obj: Union[pd.Series, pd.DataFrame]):
    if not isinstance(obj.index, pd.MultiIndex):
        obj.index = pd.MultiIndex.from_product(
            [obj.index.to_list()], names=[obj.index.name]
        )
    return obj


def _reshape(
    df: "pd.DataFrame", c: "PandasConverter"
) -> Union[pd.Series, pd.DataFrame]:
    """Reshape `df` to provide expected return types."""
    columns: "ColumnSpec" = c._context[ColumnSpec]

    if c.format is not None:
        # SDMX-CSV → no reshaping
        return df.reindex(columns=columns.full)

    # Set key columns as a pd.MultiIndex
    result = (
        df.set_index(columns.key)
        .pipe(_ensure_multiindex)
        .rename(columns={c: "value" for c in columns.measure})
    )

    # Single column for measure(s) + attribute(s) → return pd.Series
    if 1 == len(columns.obs) - len(columns.key):
        result = result.iloc[:, 0]

    # Unstack 1 or more index levels
    if columns.unstack:
        result = result.unstack(columns.unstack)

    return result


def _to_periodindex(obj: Union["pd.Series", "pd.DataFrame"], c: "PandasConverter"):
    """Convert a 1-D datetime index on `obj` to a PeriodIndex."""
    result = obj

    freq = c.datetime_freq

    # Convert to a PeriodIndex with a particular frequency
    if isinstance(freq, common.Component):
        # ID of a Dimension; Attribute; or column of `df`
        components = chain(
            c.get_components("dimensions"),
            c.get_components("attributes"),
            map(lambda id: common.Dimension(id=str(id)), result.columns.names),
        )
        try:
            component = next(filter(lambda c: c.id == freq.id, components))
        except StopIteration:
            raise ValueError(freq)

        if isinstance(component, common.Dimension):
            # Retrieve Dimension values from a pd.MultiIndex level
            level = component.id
            assert isinstance(result.columns, pd.MultiIndex)
            i = result.columns.names.index(level)
            values = set(result.columns.levels[i])
            # Remove the index level
            result.columns = result.columns.droplevel(i)
        elif isinstance(component, common.DataAttribute):  # pragma: no cover
            # Retrieve Attribute values from a column
            values = result[component.id].unique()

        if len(values) > 1:
            raise ValueError(
                f"cannot convert to PeriodIndex with non-unique freq={sorted(values)}"
            )

        # Store the unique value
        freq = values.pop()

    if freq is not None:
        assert isinstance(result.index, pd.DatetimeIndex)
        result.index = result.index.to_period(freq=freq)

    if c.datetime_axis in {1, "columns"}:
        result = result.transpose()

    return result


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


@PandasConverter.register
def convert_serieskey(c: "PandasConverter", obj: common.SeriesKey):
    return {dim: kv.value for dim, kv in obj.order().values.items()}
