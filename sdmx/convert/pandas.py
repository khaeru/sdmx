"""Convert :mod:`sdmx.message` and :mod:`.model` objects to :mod:`pandas` objects."""

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from dataclasses import InitVar, dataclass, field
from itertools import chain, product, repeat
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Optional, Union, cast
from warnings import warn

import numpy as np
import pandas as pd

from sdmx import message, urn
from sdmx.dictlike import DictLike
from sdmx.format import csv
from sdmx.format.csv.common import Attributes, CSVFormatOptions, Labels, TimeFormat
from sdmx.format.csv.v2 import Keys
from sdmx.model import common, v21, v30
from sdmx.model.internationalstring import DEFAULT_LOCALE

from .common import DispatchConverter

if TYPE_CHECKING:
    from typing import TypedDict

    from pandas.core.dtypes.base import ExtensionDtype
    from pandas.tseries.offsets import DateOffset

    from sdmx.format.csv.common import CSVFormatOptions
    from sdmx.model.common import Item
    from sdmx.model.v21 import ContentConstraint

    class ToDatetimeKeywords(TypedDict, total=False):
        format: str

    KeyOrAttributeValue = Union["common.KeyValue", "common.AttributeValue"]


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


NO_VALUE = SimpleNamespace(value="")


class Column(ABC):
    """Representation of conversion of a column.

    .. todo:: Unify with :class:`.reader.csv.Handler`.
    """

    __slots__ = ("name", "id")

    #: Column name/header.
    name: str
    #: SDMX component ID.
    id: str

    @abstractmethod
    def __call__(self, *args, **kwargs) -> str: ...

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{type(self).__name__} id={getattr(self, 'id', '—')!r} name={self.name!r}>"


class Fixed(Column):
    """Column with fixed value."""

    def __init__(self, name: str, value: str) -> None:
        self.name = name
        self._value = value

    def __call__(self) -> str:
        return self._value


class ComponentColumn(Column):
    """A column taking its header from a :class:`.Component`."""

    labels: Labels

    def __init__(self, component: "common.Component") -> None:
        self.id = component.id
        c_name = (
            str(component.concept_identity.name)
            if component.concept_identity
            else f"(Name of {component.id!r})"
        )
        # Set column header according to subclass `labels` attribute
        self.name = {
            Labels.id: self.id,
            Labels.both: f"{self.id}: {c_name}",
            Labels.name: c_name,
        }[self.labels]


class ComponentBoth(ComponentColumn):
    """:attr:`Labels.both` column."""

    labels = Labels.both

    def __call__(self, values: Mapping[str, "KeyOrAttributeValue"]) -> str:
        v = values[self.id].value
        return f"{v.id}: {v.name}" if isinstance(v, common.Code) else str(v)


class ComponentID(ComponentColumn):
    """:attr:`Labels.id` column."""

    labels = Labels.id

    def __call__(self, values: Mapping[str, "KeyOrAttributeValue"]) -> str:
        return str(values.get(self.id, NO_VALUE).value)


class ComponentName(ComponentColumn):
    """:attr:`Labels.name` column."""

    labels = Labels.name

    def __call__(self, values: Mapping[str, "KeyOrAttributeValue"]) -> str:
        v = values[self.id].value
        return str(v.name) if isinstance(v, common.Code) else v


class ColumnSpec:
    """Information about columns for conversion."""

    #: Initial columns.
    start: list[Fixed]
    #: Columns related to observation keys.
    key: list[Column]
    #: Column(s) related to observation measure(s).
    measure: list[Column]
    #: Columns related to observation-attached attributes.
    obs_attrib: list[Column]
    #: Final columns.
    end: list[Fixed]

    def __init__(
        self,
        pc: Optional["PandasConverter"] = None,
        ds: Optional["common.BaseDataSet"] = None,
    ) -> None:
        if pc is None or ds is None:
            return  # Empty/placeholder

        self.constraint = pc.constraint

        # Construct the short URN for the DFD
        dfd_urn = ""
        if pc._strict:
            if ds.described_by is None:
                raise ValueError(f"No associated data flow definition for {ds}")
            dfd_urn = urn.make(ds.described_by).partition("=")[2]

        # Either use a provided DSD, or construct one by inspecting the first
        # observation
        dsd = self._maybe_construct_dsd(
            pc._context.get(common.BaseDataStructureDefinition, None),
            ds.obs[0] if len(ds.obs) else common.BaseObservation(),
        )

        # Fixed columns
        self.start = {
            csv.common.CSVFormat: [],  # No specific SDMX-CSV format
            csv.v1.FORMAT: [Fixed("DATAFLOW", dfd_urn)],
            csv.v2.FORMAT: [
                Fixed("STRUCTURE", "dataflow"),
                Fixed("STRUCTURE_ID", dfd_urn),
                Fixed("ACTION", "I"),
            ],
        }[pc.format_options.format]

        # Identify classes for key and attribute columns
        classes = cast(
            list,
            {
                Labels.id: [ComponentID],
                Labels.both: [ComponentBoth],
                Labels.name: [ComponentID, ComponentName],
            }[pc.format_options.labels],
        )

        # Construct key columns: 1 or 2 columns for each dimension
        self.key = [cls(d) for d, cls in product(dsd.dimensions.components, classes)]

        # Measure columns
        _measures = dsd.measures.components
        if not _measures or pc.format_options.format is csv.v1.FORMAT:
            _measures = [
                v21.PrimaryMeasure(
                    id="OBS_VALUE",
                    concept_identity=common.Concept(
                        id="OBS_VALUE", name="Observation value"
                    ),
                )
            ]
        self.measure = [cls(m) for m, cls in product(_measures, classes)]

        # Attribute columns
        _attributes = dsd.attributes.components
        if pc.attributes is Attributes.none:
            # Omit attribute columns if so configured
            _attributes = []
            # Disable callback to extend self.obs_attrib
            setattr(self, "add_obs_attrib", lambda v: None)

        # Construct attribute columns: 1 or 2 columns for each attribute
        self.obs_attrib = [cls(a) for a, cls in product(_attributes, classes)]

        # Columns for attributes attached to the data set (SDMX 2.1 only)
        self.end = []
        if (pc.attributes & Attributes.dataset) and isinstance(ds, v21.DataSet):
            self.end.extend(Fixed(id, value) for id, value in ds.attrib.items())

    @staticmethod
    def _maybe_construct_dsd(
        dsd: Optional["common.BaseDataStructureDefinition"],
        obs: "common.BaseObservation",
    ) -> Union["v21.DataStructureDefinition", "v30.DataStructure"]:
        """If `dsd` is None, construct a DSD by inspection of `obs`."""
        if dsd is not None:
            return dsd

        result = v21.DataStructureDefinition()
        for dim_id in obs.key.order().values.keys():
            result.dimensions.getdefault(id=dim_id)

        for attr_id in obs.attrib:
            result.attributes.getdefault(id=attr_id)

        return result

    @property
    def assign(self) -> Mapping[str, str]:
        """Return values for :meth:`pandas.DataFrame.assign`."""
        return {c.name: c() for c in self.start + self.end}

    @property
    def full(self) -> list[str]:
        """Full list of column names."""
        return [c.name for c in self.start] + self.obs + [c.name for c in self.end]

    @property
    def obs(self) -> list[str]:
        """List of column names for observation data."""
        return [c.name for c in chain(self.key, self.measure, self.obs_attrib)]

    def add_obs_attrib(self, values: Iterable[str]) -> None:
        """Extend :attr:`obs_attrib` using `values`."""
        if missing := set(values) - set(c.id for c in self.obs_attrib):
            # Convert missing attributes to DataAttribute → Columns
            self.obs_attrib.extend(
                ComponentID(common.DataAttribute(id=id))
                for id in filter(missing.__contains__, values)
            )

    def convert_obs(self, obs: "common.BaseObservation") -> list:
        """Convert a single Observation to a data row.

        The items of the result correspond to the column names in :attr:`obs`.
        """
        key = obs.key
        if self.constraint and key not in self.constraint:
            # Emit an empty row to be dropped
            result: Iterable[Union[str, None]] = repeat(None, len(self.obs))
        else:
            # Observation values
            # FIXME Handled CodedObservationValue, similar to AttributeValue
            ov = None if obs.value is None else str(obs.value)

            # Combined attributes from observation, series-, and group keys
            avs = obs.attrib

            # Maybe update list of observation attributes
            self.add_obs_attrib(avs)

            # - Convert the observation Key using key Columns.
            # - Convert the value to Optional[str].
            # - Convert the attribute values using attribute Columns.
            result = chain(
                [c(key.values) for c in self.key],
                [ov] * len(self.measure),
                [c(avs) for c in self.obs_attrib],
            )
        return list(result)


@dataclass
class PandasConverter(DispatchConverter):
    """Convert SDMX messages and IM objects to :class:`pandas.DataFrame` and similar.

    PandasConverter implements a dispatch pattern according to the type of the object
    to be converted. The attributes/arguments to the class control the conversion
    behaviour and return types.
    """

    #: SDMX-CSV format options.
    format_options: "CSVFormatOptions" = field(default_factory=CSVFormatOptions)

    #: Attributes to include.
    attributes: Attributes = Attributes.none

    #: If given, only Observations included by the *constraint* are returned.
    constraint: Optional["ContentConstraint"] = None

    #: Datatype for observation values. If :any:`None`, data values remain
    #: :class:`object`/:class:`str`.
    dtype: Union[type["np.generic"], type["ExtensionDtype"], str, None] = np.float64

    #: Axis on which to place a time dimension. One of:
    #:
    #: - :py:`-1`: disabled.
    #: - :py:`0, "index"`: first/index axis.
    #: - :py:`1, "columns"`: second/columns axis.
    datetime_axis: Union[int, str] = -1

    #: Dimension to convert to :class:`pandas.DatetimeIndex`. A :class:`str` value is
    #: interpreted as a dimension ID.
    datetime_dimension: Optional["common.DimensionComponent"] = None

    #: Frequency for conversion to :class:`pandas.PeriodIndex`. A :class:`str` value is
    #: interpreted as one of the :ref:`pd:timeseries.period_aliases`.
    datetime_freq: Optional["DateOffset"] = None

    #: include : iterable of str or str, optional
    #:     One or more of the attributes of the StructureMessage ('category_scheme',
    #:     'codelist', etc.) to transform.
    include: set[str] = field(default_factory=lambda: set(ALL_CONTENTS))

    locale: str = DEFAULT_LOCALE

    #: :any:`True` to convert datetime.
    #:
    #: .. deprecated:: 2.23.0
    #:
    #:    Use :attr:`datetime_axis`, :attr:`datetime_dimension`, or
    #:    :attr:`datetime_freq`.
    datetime: InitVar = None

    #: Return type for :func:`.convert_dataset` and similar methods.
    #:
    #: .. deprecated:: 2.23.0
    #:
    #:    User code should instead explicitly modify the returned
    #:    :class:`~pandas.DataFrame` or :class:`~pandas.Series`.
    rtype: InitVar[str] = ""

    # Internal variables
    _columns: "ColumnSpec" = field(default_factory=ColumnSpec)

    # True if converting to SDMX-CSV
    _strict: bool = False

    # Columns to be set as index levels, then unstacked.
    _unstack: list[str] = field(default_factory=list)

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
            self._unstack = [
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
        if isinstance(
            self.format_options, csv.v2.FormatOptions
        ) and self.format_options.keys not in {Keys.none}:
            raise NotImplementedError(
                f"convert to SDMX-CSV with keys={self.format_options.keys}"
            )
        elif self.format_options.time_format not in {TimeFormat.original}:
            raise NotImplementedError(
                f"convert to SDMX-CSV with time_format={self.format_options.time_format}"
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

        # Set private attributes
        self._strict = issubclass(
            self.format_options.format, (csv.v1.FORMAT, csv.v2.FORMAT)
        )


def to_pandas(obj, **kwargs):
    """Convert an SDMX `obj` to :mod:`pandas` object(s).

    `kwargs` can include any of the attributes of :class:`.PandasConverter`.

    Other parameters
    ----------------
    format_options :
        if not given, an instance of :class:`.CSVFormatOptions` is used as a default.
    labels :
        if given, the :attr:`.CSVFormatOptions.labels` attribute of the `format_options`
        keyword argument is replaced.
    time_format :
        if given, the :attr:`.CSVFormatOptions.time_format` attribute of the
        `format_options` keyword argument is replaced.

    .. versionchanged:: 1.0

       :func:`.to_pandas` handles all types of objects,
       replacing the earlier, separate ``data2pandas`` and ``structure2pd`` writers.

    .. versionchanged:: 2.23.0

       :func:`.to_pandas` is a thin wrapper for :class:`.PandasConverter`.
    """
    csv.common.kwargs_to_format_options(kwargs, csv.common.CSVFormatOptions)
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
    # Handle the deprecated rtype="compat" argument
    c.handle_compat()

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
    c._context[common.BaseDataSet] = obj
    c._columns = ColumnSpec(pc=c, ds=obj)

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
        pd.DataFrame(map(c._columns.convert_obs, obj.obs))
        .dropna(how="all")
        .set_axis(c._columns.obs, axis=1)  # NB This must come after DataFrame(map(…))
        .assign(**c._columns.assign)
        .pipe(_apply_dtype, c)
        .pipe(_convert_datetime, c)
        .pipe(_reshape, c)
        .pipe(_to_periodindex, c)
    )

    c._context.pop(common.BaseDataSet)

    return result


def _apply_dtype(df: "pd.DataFrame", c: "PandasConverter") -> "pd.DataFrame":
    """Apply `dtype` to 0 or more `columns`."""
    if c.dtype is None:
        return df

    # Create a mapping to apply `dtype` to multiple columns
    measure_cols = {c.name for c in c._columns.measure}
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
    c._unstack = c._unstack or list(map(str, filter(lambda d: d.id != dim.id, dims)))

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

    if c._strict:
        # SDMX-CSV → no reshaping
        return df.reindex(columns=c._columns.full)

    # Set key columns as a pd.MultiIndex
    result = (
        df.set_index([col.name for col in c._columns.key])
        .pipe(_ensure_multiindex)
        .rename(columns={c.name: "value" for c in c._columns.measure})
    )

    # Single column for measure(s) + attribute(s) → return pd.Series
    if 1 == len(c._columns.obs) - len(c._columns.key):
        result = result.iloc[:, 0]

    # Unstack 1 or more index levels
    if c._unstack:
        result = result.unstack(c._unstack)

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
