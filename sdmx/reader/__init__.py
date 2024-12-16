from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Union
from warnings import warn

from . import csv, json, xml

if TYPE_CHECKING:
    import io
    from typing import TypeVar

    import sdmx.message
    import sdmx.reader.base

    T = TypeVar("T", bound=sdmx.reader.base.Converter)


#: All converters. Application code **may** extend this collection with custom
#: sub-classes of :class:`.Converter`.
CONVERTER = [csv.DataFrameConverter, csv.Reader, json.Reader, xml.Reader]

#: Only Readers for standard SDMX formats.
READERS = [csv.Reader, json.Reader, xml.Reader]


def detect_content_reader(content) -> type["sdmx.reader.base.BaseReader"]:
    """Return a reader class for :class:`bytes` `content`.

    .. deprecated:: 2.20.0
       Use :func:`get_reader` instead.
    """
    warn(
        "detect_content_reader(bytes); use get_reader() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return get_reader(content)


def _get(data: Any, kwargs: Optional[dict], _classes: list[type["T"]]) -> type["T"]:
    for c in _classes:
        if c.handles(data, kwargs or {}):
            return c

    raise ValueError(
        f"{data!r} not recognized by any of "
        + ", ".join(map(lambda c: c.__name__, _classes))
    )


def get_converter(
    data: Any, kwargs: Optional[dict] = None
) -> type["sdmx.reader.base.Converter"]:
    """Identify a :class:`Converter` or :class:`.Reader` for `data`.

    For each class in :data:`CONVERTER`, the :meth:`.Converter.handles` or
    :meth:`.BaseReader.handles` method is called with `data` and `kwargs`.

    `data` may include:

    - :class:`bytes` —same behaviour as deprecated :func:`.detect_content_reader`.
    - :class:`requests.Response` —same behaviour as deprecated
      :func:`.get_reader_for_media_type`.
    - :class:`pathlib.Path` —same behaviour as deprecated :func:`.get_reader_for_path`.

    …or, anything else that is handled by a class listed in :data:`CONVERTER`.

    Raises
    ------
    ValueError
        if none of the Converter classes can convert `data` and `kwargs` to SDMX.
    """
    return _get(data, kwargs, CONVERTER)


def get_reader(
    data: Any,
    kwargs: Optional[dict] = None,
    _classes: list[type["sdmx.reader.base.BaseReader"]] = READERS,
) -> type["sdmx.reader.base.BaseReader"]:
    """Identify a :class:`.Reader` for `data`.

    Identical to :func:`.get_converter`, except only :data:`READERS` for SDMX standard
    formats are returned.
    """
    return _get(data, kwargs, READERS)


def get_reader_for_media_type(value) -> type["sdmx.reader.base.BaseReader"]:
    """Return a reader class for HTTP content/media type `value`.

    .. deprecated:: 2.20.0
       Use :func:`get_reader` instead.
    """
    from requests import Response

    warn(
        "get_reader_for_media_type(str); use get_reader(requests.Response) instead",
        DeprecationWarning,
        stacklevel=2,
    )

    # Use `value` as Content-Type header for an otherwise-empty Response
    resp = Response()
    resp.headers["content-type"] = value

    try:
        return get_reader(resp)
    except ValueError as e:
        *_, names = e.args[0].partition(" any of ")
        raise ValueError(f"Media type {value!r} not supported by any of {names}")


def get_reader_for_path(path) -> type["sdmx.reader.base.BaseReader"]:
    """Return a reader class for file `path`.

    .. deprecated:: 2.20.0
       Use :func:`get_reader` instead.
    """
    warn(
        "get_reader_for_path(…); use get_reader() instead",
        DeprecationWarning,
        stacklevel=2,
    )

    p = Path(path)
    try:
        return get_reader(p)
    except ValueError as e:
        *_, names = e.args[0].partition(" any of ")
        raise ValueError(f"File suffix {p.suffix!r} not supported by any of {names}")


def read_sdmx(
    filename_or_obj: Union[bytes, str, Path, "io.IOBase", "io.BufferedReader"],
    format: Optional[str] = None,
    **kwargs,
) -> "sdmx.message.Message":
    """Read a :class:`.Message` from a path, file, or stream in an SDMX standard format.

    To identify whether `filename_or_obj` contains SDMX-CSV, SDMX-JSON, or SDMX-ML,
    :meth:`.BaseReader.handles` is called.

    Parameters
    ----------
    filename_or_obj :
        may include:

        - :class:`str` or :class:`pathlib.Path`: path to a particular file.
        - :class:`bytes`: raw/binary SDMX content.
        - :class:`io.IOBase`: a buffer, opened file, or other I/O object containing
          binary SDMX content.
    format : 'CSV', 'XML', or 'JSON', optional
        force handling `filename_or_obj` as if it had the given extension, even if
        :meth:`~.BaseReader.handles` fails to match.

    Other Parameters
    ----------------
    structure :
        :class:`.Structure`, :class:`.StructureUsage`, or other information used by a
        :class:`.BaseReader` to interpret the content of `filename_or_obj`. For example,
        the :class:`DataStructureDefinition <.BaseDataStructureDefinition>` for a
        structure-specific SDMX-ML message.
    """
    if isinstance(filename_or_obj, (str, Path)):
        path = Path(filename_or_obj)  # Ensure Path type
        obj: Union[bytes, "io.IOBase"] = open(path, "rb")  # Open the file
    else:
        path, obj = None, filename_or_obj

    # Try to identify a reader by first the path, then by the `obj` content
    for candidate in path, obj, Path(f"_.{(format or 'MISSING').lower()}"):
        try:
            reader = get_reader(candidate, kwargs)
        except ValueError:
            reader = None
        else:
            break

    if not reader:
        raise RuntimeError(
            f"cannot infer SDMX message format from path {path!r}, format "
            f"hint={format}, or content"
        )

    return reader().convert(obj, **kwargs)


def to_sdmx(data, **kwargs) -> "sdmx.message.Message":
    """Convert `data` in non-SDMX formats and data structures to SDMX :class:`.Message`.

    Unlike :func:`.read_sdmx`, which handles only the standard SDMX formats SDMX-CSV,
    SDMX-JSON, and SDMX-ML, this method can will process any Python data structure
    handled by a known :data:`CONVERTER`.
    """
    try:
        converter = get_converter(data, kwargs)
    except ValueError:
        raise NotImplementedError(f"Convert {type(data)} {data!r} to SDMX")

    return converter().convert(data, **kwargs)
