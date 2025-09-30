""":ref:`sdmx-csv` writer."""

from os import PathLike
from typing import TYPE_CHECKING, Optional, Union

import pandas as pd

from sdmx.convert.pandas import PandasConverter
from sdmx.format.csv import common, v2

if TYPE_CHECKING:
    from sdmx.message import DataMessage
    from sdmx.model.common import BaseDataSet


def to_csv(
    obj: Union["DataMessage", "BaseDataSet"],
    *,
    path: Optional[PathLike] = None,
    rtype: type[Union[str, pd.DataFrame]] = str,
    **kwargs,
) -> Union[None, str, pd.DataFrame]:
    """Convert an SDMX *obj* to SDMX-CSV.

    With :py:`rtype=pandas.DataFrame`, the returned object is **not necessarily** valid
    SDMX-CSV. In particular, writing this to file using :meth:`pandas.DataFrame.to_csv`
    will yield invalid SDMX-CSV, because pandas includes a CSV column corresponding to
    the index of the data frame. You must pass :py:`index=False` to disable this
    behaviour. With :py:`rtype=str` or when giving `path`, this is done automatically.

    Parameters
    ----------
    path : os.PathLike, optional
        Path to write an SDMX-CSV file.
    rtype :
        Return type; see below. Pass literally :class:`str` or
        :class:`pandas.DataFrame`; *not* an instance of either class.

    Other parameters
    ----------------
    kwargs :
        Keyword arguments passed to :class:`.PandasConverter` and
        :class:`.format.csv.v1.FormatOptions`.

    Returns
    -------
    None :
        if `path` is given.
    str :
        if `rtype` is :class:`str`.
    pd.DataFrame :
        if `rtype` is :class:`~pandas.DataFrame`.

    Raises
    ------
    NotImplementedError
        If `obj` is any class except :class:`.DataSet`; this is the only class for which
        the SDMX-CSV standard describes a format.

        The two optional parameters are exactly as described in the specification.

        Because SDMX-CSV includes a column with an identifier (partial URN) for the
        dataflow to which the data belong (the column is named differently according to
        format version; see :ref:`sdmx-csv`), it is mandatory that the
        :attr:`DataSet.described_by <.BaseDataSet.described_by>` attribute of `obj`
        gives an association to an object from which a :class:`.URN` can be constructed.

    NotImplementedError
        if the `kwargs` include :py:`labels="name"` or :py:`time_format="normalized"`.
    ValueError
        If :attr:`DataSet.described_by <.BaseDataSet.described_by>` is :any:`None`.

    See also
    --------
    :ref:`sdmx.writer.csv <writer-csv>`.
    """
    common.kwargs_to_format_options(kwargs, v2.FormatOptions)
    result = PandasConverter(**kwargs).convert(obj)

    if path:
        return result.to_csv(path, index=False)
    elif rtype is str:
        return result.to_string(index=False)
    elif rtype is pd.DataFrame:
        return result
    else:
        raise ValueError(f"Invalid rtype={rtype!r}")
