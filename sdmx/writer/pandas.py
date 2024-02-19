from itertools import chain
from typing import Any, Dict, Hashable, Set, Union

import numpy as np
import pandas as pd

from sdmx import message
from sdmx.dictlike import DictLike
from sdmx.model import v21 as model
from sdmx.model.v21 import (
    DEFAULT_LOCALE,
    AllDimensions,
    DataAttribute,
    DataSet,
    Dimension,
    DimensionComponent,
    Item,
    Observation,
    SeriesKey,
    TimeDimension,
)
from sdmx.writer.base import BaseWriter

#: Default return type for :func:`write_dataset` and similar methods. Either 'compat' or
#: 'rows'. See the ref:`HOWTO <howto-rtype>`.
DEFAULT_RTYPE = "rows"

_HAS_PANDAS_2 = pd.__version__.split(".")[0] >= "2"


writer = BaseWriter("pandas")


def to_pandas(obj, *args, **kwargs):
    """Convert an SDMX *obj* to :mod:`pandas` object(s).

    See :ref:`sdmx.writer.pandas <writer-pandas>`.
    """
    return writer.recurse(obj, *args, **kwargs)


# Functions for Python containers
@writer
def _list(obj: list, *args, **kwargs):
    """Convert a :class:`list` of SDMX objects."""
    if isinstance(obj[0], Observation):
        return write_dataset(model.DataSet(obs=obj), *args, **kwargs)
    elif isinstance(obj[0], DataSet) and len(obj) == 1:
        return writer.recurse(obj[0], *args, **kwargs)
    elif isinstance(obj[0], SeriesKey):
        assert len(args) == len(kwargs) == 0
        return write_serieskeys(obj)
    else:
        return [writer.recurse(item, *args, **kwargs) for item in obj]


@writer
def _dict(obj: dict, *args, **kwargs):
    """Convert mappings."""
    result = {k: writer.recurse(v, *args, **kwargs) for k, v in obj.items()}

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


@writer
def _set(obj: set, *args, **kwargs):
    """Convert :class:`set`."""
    result = {writer.recurse(o, *args, **kwargs) for o in obj}
    return result


# Functions for message classes
@writer
def write_datamessage(obj: message.DataMessage, *args, rtype=None, **kwargs):
    """Convert :class:`.DataMessage`.

    Parameters
    ----------
    rtype : 'compat' or 'rows', optional
        Data type to return; default :data:`.DEFAULT_RTYPE`. See the
        :ref:`HOWTO <howto-rtype>`.
    kwargs :
        Passed to :meth:`write_dataset` for each data set.

    Returns
    -------
    :class:`pandas.Series` or :class:`pandas.DataFrame`
        if `obj` has only one data set.
    list of (:class:`pandas.Series` or :class:`pandas.DataFrame`)
        if `obj` has more than one data set.
    """
    # Pass the message's DSD to assist datetime handling
    assert obj.dataflow
    kwargs.setdefault("dsd", obj.dataflow.structure)

    # Pass the return type and associated information
    kwargs["_rtype"] = rtype or DEFAULT_RTYPE
    if kwargs["_rtype"] == "compat":
        kwargs["_message_class"] = obj.__class__
        kwargs["_observation_dimension"] = obj.observation_dimension

    if len(obj.data) == 1:
        return writer.recurse(obj.data[0], *args, **kwargs)
    else:
        return [writer.recurse(ds, *args, **kwargs) for ds in obj.data]


@writer
def write_structuremessage(obj: message.StructureMessage, include=None, **kwargs):
    """Convert :class:`.StructureMessage`.

    Parameters
    ----------
    obj : .StructureMessage
    include : iterable of str or str, optional
        One or more of the attributes of the StructureMessage ('category_scheme',
        'codelist', etc.) to transform.
    kwargs :
        Passed to :meth:`write` for each attribute.

    Returns
    -------
    .DictLike
        Keys are StructureMessage attributes; values are pandas objects.
    """
    all_contents = {
        "category_scheme",
        "codelist",
        "concept_scheme",
        "constraint",
        "dataflow",
        "structure",
        "organisation_scheme",
    }

    # Handle arguments
    if include is None:
        attr_set = all_contents
    else:
        attr_set = set([include] if isinstance(include, str) else include)
        # Silently discard invalid names
        attr_set &= all_contents
    attrs = sorted(attr_set)

    result: DictLike[str, Union[pd.Series, pd.DataFrame]] = DictLike()
    for a in attrs:
        dl = writer.recurse(getattr(obj, a), **kwargs)
        if len(dl):
            # Only add non-empty elements
            result[a] = dl

    return result


# Functions for model classes


@writer
def _c(obj: model.Component):
    """Convert :class:`.Component`."""
    # Raises AttributeError if the concept_identity is missing
    return str(obj.concept_identity.id)  # type: ignore


@writer
def _cc(obj: model.ContentConstraint, **kwargs):
    """Convert :class:`.ContentConstraint`."""
    return {
        i: writer.recurse(cr, **kwargs) for i, cr in enumerate(obj.data_content_region)
    }


@writer
def _cr(obj: model.CubeRegion, **kwargs):
    """Convert :class:`.CubeRegion`."""
    result: DictLike[str, pd.Series] = DictLike()
    for dim, ms in obj.member.items():
        result[dim.id] = pd.Series(
            [writer.recurse(sv, **kwargs) for sv in ms.values], name=dim.id
        )
    return result


@writer
def _rp(obj: model.RangePeriod, **kwargs):
    """Convert :class:`.RangePeriod`."""
    return f"{obj.start.period}–{obj.end.period}"


@writer
def write_dataset(  # noqa: C901 TODO reduce complexity 12 → ≤11
    obj: model.DataSet,
    attributes="",
    dtype=np.float64,
    constraint=None,
    datetime=False,
    **kwargs,
):
    """Convert :class:`~.DataSet`.

    See the :ref:`walkthrough <datetime>` for examples of using the `datetime` argument.

    Parameters
    ----------
    obj : :class:`~.DataSet` or iterable of :class:`Observation <.BaseObservation>`
    attributes : str
        Types of attributes to return with the data. A string containing zero or more
        of:

        - ``'o'``: attributes attached to each :class:`Observation <.BaseObservation>` .
        - ``'s'``: attributes attached to any (0 or 1) :class:`~.SeriesKey` associated
          with each Observation.
        - ``'g'``: attributes attached to any (0 or more) :class:`~.GroupKey` associated
          with each Observation.
        - ``'d'``: attributes attached to the :class:`~.DataSet` containing the
          Observations.

    dtype : str or :class:`numpy.dtype` or None
        Datatype for values. If None, do not return the values of a series. In this
        case, `attributes` must not be an empty string so that some attribute is
        returned.
    constraint : .ContentConstraint, optional
        If given, only Observations included by the *constraint* are returned.
    datetime : bool or str or or .Dimension or dict, optional
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

    Returns
    -------
    :class:`pandas.DataFrame`
        - if `attributes` is not ``''``, a data frame with one row per Observation,
          ``value`` as the first column, and additional columns for each attribute;
        - if `datetime` is given, various layouts as described above; or
        - if `_rtype` (passed from :func:`write_datamessage`) is 'compat', various
          layouts as described in the :ref:`HOWTO <howto-rtype>`.
    :class:`pandas.Series` with :class:`pandas.MultiIndex`
        Otherwise.
    """
    # If called directly on a DataSet (rather than a parent DataMessage), cannot
    # determine the "dimension at observation level"
    rtype = kwargs.setdefault("_rtype", "rows")

    # Validate attributes argument
    attributes = attributes or ""
    try:
        attributes = attributes.lower()
    except AttributeError:
        raise TypeError("'attributes' argument must be str")

    if rtype == "compat" and kwargs["_observation_dimension"] is not AllDimensions:
        # Cannot return attributes in this case
        attributes = ""
    elif set(attributes) - {"o", "s", "g", "d"}:
        raise ValueError(f"attributes must be in 'osgd'; got {attributes}")

    # Iterate on observations
    data: Dict[Hashable, Dict[str, Any]] = {}
    for observation in obj.obs:
        # Check that the Observation is within the constraint, if any
        key = observation.key.order()
        if constraint and key not in constraint:
            continue

        # Add value and attributes
        row = {}
        if dtype:
            row["value"] = observation.value
        if attributes:
            # Add the combined attributes from observation, series- and group keys
            row.update(observation.attrib)
        if "d" in attributes:
            # Add the attributes of the data set
            row.update(obj.attrib)

        data[tuple(map(str, key.get_values()))] = row

    # NB mypy errors here on CI, but not locally
    result: Union[pd.Series, pd.DataFrame] = pd.DataFrame.from_dict(
        data,
        orient="index",  # type: ignore [arg-type]
    )

    if len(result):
        result.index.names = observation.key.order().values.keys()
        if dtype:
            result["value"] = result["value"].astype(dtype)
            if not attributes:
                result = result["value"]

    # Reshape for compatibility with v0.9
    result, datetime, kwargs = _dataset_compat(result, datetime, kwargs)
    # Handle the datetime argument, if any
    return _maybe_convert_datetime(result, datetime, obj=obj, **kwargs)


def _dataset_compat(df, datetime, kwargs):
    """Helper for :meth:`.write_dataset` 0.9 compatibility."""
    rtype = kwargs.pop("_rtype")
    if rtype != "compat":
        return df, datetime, kwargs  # Do nothing

    # Remove compatibility arguments from kwargs
    kwargs.pop("_message_class")
    obs_dim = kwargs.pop("_observation_dimension")

    if isinstance(obs_dim, list) and len(obs_dim) == 1:
        # Unwrap a length-1 list
        obs_dim = obs_dim[0]

    if obs_dim in (AllDimensions, None):
        pass  # Do nothing
    elif isinstance(obs_dim, TimeDimension):
        # Don't modify *df*; only change arguments so that _maybe_convert_datetime
        # performs the desired changes
        if datetime is False or datetime is True:
            # Either datetime is not given, or True without specifying a dimension;
            # overwrite
            datetime = obs_dim
        elif isinstance(datetime, dict):
            # Dict argument; ensure the 'dim' key is the same as obs_dim
            if datetime.setdefault("dim", obs_dim) != obs_dim:
                msg = (
                    f"datetime={datetime} conflicts with rtype='compat' and"
                    f" {obs_dim} at observation level"
                )
                raise ValueError(msg)
        else:
            assert datetime == obs_dim, (datetime, obs_dim)
    elif isinstance(obs_dim, DimensionComponent):
        # Pivot all levels except the observation dimension
        df = df.unstack([n for n in df.index.names if n != obs_dim.id])
    else:
        # E.g. some JSON messages have two dimensions at the observation level;
        # behaviour is unspecified here, so do nothing.
        pass

    return df, datetime, kwargs


def _maybe_convert_datetime(df, arg, obj, dsd=None):  # noqa: C901
    """Helper for :meth:`.write_dataset` to handle datetime indices.

    Parameters
    ----------
    df : pandas.DataFrame
    arg : dict
        From the `datetime` argument to :meth:`write_dataset`.
    obj :
        From the `obj` argument to :meth:`write_dataset`.
    dsd: ~.DataStructureDefinition, optional
    """
    # TODO Simplify this method to reduce its McCabe complexity from 23 to <= 13

    # Check argument values
    param = dict(dim=None, axis=0, freq=False)

    if not arg:
        return df  # False, None, empty dict → no datetime conversion
    elif isinstance(arg, str):
        param["dim"] = arg
    elif isinstance(arg, DimensionComponent):
        param["dim"] = arg.id
    elif isinstance(arg, dict):
        extra_keys = set(arg.keys()) - set(param.keys())
        if extra_keys:
            raise ValueError(extra_keys)
        param.update(arg)
    elif isinstance(arg, bool):
        pass  # True
    else:
        raise ValueError(arg)

    def _get(kind: str):
        """Return an appropriate list of dimensions or attributes."""
        if len(getattr(obj.structured_by, kind).components):
            return getattr(obj.structured_by, kind).components
        elif dsd:
            return getattr(dsd, kind).components
        else:
            return []

    # Determine time dimension
    if not param["dim"]:
        for dim in filter(lambda d: isinstance(d, TimeDimension), _get("dimensions")):
            param["dim"] = dim
            break
    if not param["dim"]:
        raise ValueError(f"no TimeDimension in {_get('dimensions')}")

    # Unstack all but the time dimension and convert
    other_dims = list(filter(lambda d: d != param["dim"], df.index.names))
    df = df.unstack(other_dims)
    # Only provide format in pandas >= 2.0.0
    kw = dict(format="mixed") if _HAS_PANDAS_2 else {}
    df.index = pd.to_datetime(df.index, **kw)

    # Convert to a PeriodIndex with a particular frequency
    if freq := param["freq"]:
        try:
            # A frequency string recognized by pandas.PeriodDtype
            if isinstance(freq, str):
                freq = pd.PeriodDtype(freq=freq).freq
        except ValueError:
            # ID of a Dimension; Attribute; or column of `df`
            result = None
            for component in chain(
                _get("dimensions"), _get("attributes"), map(Dimension, df.columns.names)
            ):
                if component.id == freq:
                    freq = result = component
                    break

            if not result:
                raise ValueError(freq)

        if isinstance(freq, Dimension):
            # Retrieve Dimension values from pd.MultiIndex level
            level = freq.id
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
        elif isinstance(freq, DataAttribute):  # pragma: no cover
            raise NotImplementedError

        df.index = df.index.to_period(freq=freq)

    if param["axis"] in {1, "columns"}:
        # Change axis
        df = df.transpose()

    return df


@writer
def _dd(obj: model.DimensionDescriptor):
    """Convert :class:`.DimensionDescriptor`."""
    return writer.recurse(obj.components)


@writer
def write_itemscheme(obj: model.ItemScheme, locale=DEFAULT_LOCALE):
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
    seen: Set[Item] = set()

    def add_item(item):
        """Recursive helper for adding items."""
        # Track seen items
        if item in seen:
            return
        else:
            seen.add(item)

        items[item.id] = dict(
            # Localized name
            name=item.name.localized_default(locale),
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
        result = result["name"].rename(obj.name.localized_default(locale))

    return result


@writer
def _mv(obj: model.MemberValue):
    return obj.value


@writer
def _na(obj: model.NameableArtefact):
    return str(obj.name)


def write_serieskeys(obj):
    result = []
    for sk in obj:
        result.append({dim: kv.value for dim, kv in sk.order().values.items()})
    # TODO perhaps return as a pd.MultiIndex if that is more useful
    return pd.DataFrame(result)
