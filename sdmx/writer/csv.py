"""SDMX-CSV 1.0 writer.

See :ref:`sdmx-csv`.
"""
from os import PathLike
from typing import Literal, Optional, Type, Union

import pandas as pd

from sdmx import urn
from sdmx.model import v21 as model

from .base import BaseWriter
from .pandas import writer as pandas_writer

writer = BaseWriter("csv")


def to_csv(
    obj,
    *args,
    path: Optional[PathLike] = None,
    rtype: Type[Union[str, pd.DataFrame]] = str,
    **kwargs,
) -> Union[None, str, pd.DataFrame]:
    """Convert an SDMX *obj* to SDMX-CSV.

    With `rtype` = :class:`~pandas.DataFrame`, the returned object is
    **not necessarily** in SDMX-CSV format. In particular, writing this to file using
    :meth:`pandas.DataFrame.to_csv` will yield **invalid** SDMX-CSV, because pandas
    includes a CSV column corresponding to the index of the data frame. You must pass
    `index=False` to disable this behaviour. With `rtype` = :class:`str` or when giving
    `path`, this is done automatically.

    Parameters
    ----------
    path : os.PathLike, optional
        Path to write an SDMX-CSV file.
        If given, nothing is returned.
    rtype :
        Return type; see below. Pass literally ``str`` or ``pd.DataFrame``; *not* an
        instance of either class.

    Other parameters
    ----------------
    kwargs :
        Keyword arguments passed to :func:`.dataset`.

    Returns
    -------
    str :
        if `rtype` is :class:`str`.
    pd.DataFrame :
        if `rtype` is :class:`~pandas.DataFrame`.

    Raises
    ------
    NotImplementedError
        If `obj` is any class except :class:`.DataSet`; this is the only class for which
        the SDMX-CSV standard describes a format.

    See also
    --------
    :ref:`sdmx.writer.csv <writer-csv>`.
    """
    result = writer.recurse(obj, *args, **kwargs)

    if path:
        return result.to_csv(path, index=False)
    elif rtype is str:
        return result.to_string(index=False)
    elif rtype is pd.DataFrame:
        return result
    else:
        raise ValueError(f"Invalid rtype={rtype!r}")


@writer
def dataset(
    obj: model.DataSet,
    *,
    labels: Literal["id", "both"] = "id",
    time_format: Literal["original", "normalized"] = "original",
    **kwargs,
) -> pd.DataFrame:
    """Convert :class:`.DataSet`.

    The two optional parameters are exactly as described in the specification.

    Because SDMX-CSV includes a ``DATAFLOW`` column with an identifier (partial URN) for
    the dataflow to which the data conform, it is mandatory that the
    :attr:`~.DataSet.described_by` attribute of `obj` gives an association to a
    :class:`.DataflowDefinition` object, from which a :mod:`.urn` can be constructed.

    Parameters
    ----------
    labels : "id" or "both", optional
        “id”
           Display only :attr:`Dimension.id` / :attr:`DataAttribute.id` in column
           headers and :attr:`Code.id` in data rows.
        “both”
           Display both the ID and the localized :attr:`NameableArtefact.name`. Not yet
           implemented.
    time_format : "original" or "normalized", optional
        “original”
           Values for any dimension or attribute with ID ``TIME_PERIOD`` are displayed
           as recorded.
        “normalized”
           ``TIME_PERIOD`` values are converted to the most granular ISO 8601
           representation taking into account the highest frequency of the data in the
           message and the moment in time when the lower-frequency values were
           collected. Not yet implemented.

        This parameter is called `timeFormat` in the spec and in HTTP Accept headers.

    Other parameters
    ----------------
    kwargs :
        Keyword arguments passed to :func:`.to_pandas`. In particular, `attributes` is
        useful to control which attribute values are included in the returned CSV.

    Returns
    -------
    pandas.DataFrame

    Raises
    ------
    NotImplementedError
        For ``labels="both"`` or ``time_format="normalized"``.
    ValueError
        If :attr:`.DataSet.described_by` is :data:`None`.
    """
    if labels == "both":
        raise NotImplementedError(f"labels={labels}")
    elif time_format != "original":
        raise NotImplementedError(f"time_format={time_format}")

    # Use .writer.pandas for the conversion
    tmp = (
        pandas_writer.recurse(obj, **kwargs)
        .reset_index()
        .rename(columns={"value": "OBS_VALUE"})
    )

    # Construct the DATAFLOW column
    if obj.described_by is None:
        raise ValueError(f"No associated data flow definition for {obj}")
    dfd_urn = urn.make(obj.described_by).split("=", maxsplit=1)[1]
    df_col = pd.Series(dfd_urn, index=tmp.index, name="DATAFLOW")

    return pd.concat([df_col, tmp], axis=1)
