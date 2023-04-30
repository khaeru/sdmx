"""SDMX-CSV 1.0 writer.

SDMX-CSV version 1.0 corresponds to SDMX version 2.1.
See `the specification <https://github.com/sdmx-twg/sdmx-csv/tree/v1.0>`__ on GitHub.
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

    See :ref:`sdmx.writer.csv <writer-csv>`.
    """
    result = writer.recurse(obj, *args, **kwargs)

    if path:
        return result.to_csv(path, index=False)
    elif rtype is str:
        return result.to_string(index=False)
    elif rtype is pd.DataFrame:
        return result
    else:
        raise ValueError(f"Unknown rtype={rtype!r}")


@writer
def _ds(
    obj: model.DataSet,
    *args,
    labels: Literal["id", "both"] = "id",
    time_format: Literal["original", "normalized"] = "original",
    **kwargs,
):
    """Convert :class:`.DataSet`.

    The two optional parameters are exactly as described in the specification.

    Parameters
    ----------

    """
    # Check arguments
    if len(args):
        raise ValueError(
            f"to_csv() does not accept any positional arguments; got {args}"
        )
    if labels == "both":
        raise NotImplementedError(f"labels={labels}")
    if time_format != "original":
        raise NotImplementedError(f"time_format={time_format}")

    # Use .writer.pandas for the conversion
    tmp = (
        pandas_writer.recurse(obj, **kwargs)
        .reset_index()
        .rename(columns={"value": "OBS_VALUE"})
    )

    # Construct the DATAFLOW column
    if obj.described_by is None:
        raise ValueError(f"No associated data flow definition for {obj!r}")
    dfd_urn = urn.make(obj.described_by).split("=", maxsplit=1)[1]
    df_col = pd.Series(dfd_urn, index=tmp.index, name="DATAFLOW")

    return pd.concat([df_col, tmp], axis=1)
