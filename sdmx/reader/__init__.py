from pathlib import Path

from . import json, xml

#: Reader classes
READERS = [json.Reader, xml.Reader]


def _readers():
    return ", ".join(map(lambda cls: cls.__name__, READERS))


def detect_content_reader(content):
    """Return a reader class for `content`.

    The :meth:`.BaseReader.detect` method for each class in :data:`READERS` is called;
    if a reader signals that it is compatible with `content`, then that class is
    returned.

    Raises
    ------
    ValueError
        If no reader class matches.
    """
    for cls in READERS:
        if cls.detect(content):
            return cls

    raise ValueError(f"{repr(content)} not recognized by any of {_readers()}")


def get_reader_for_media_type(value):
    """Return a reader class for HTTP content/media type `value`.

    Raises
    ------
    ValueError
        If no reader class matches.

    See also
    --------
    BaseReader.media_type
    """
    for cls in READERS:
        if cls.handles_media_type(value):
            return cls

    raise ValueError(f"Media type {value!r} not supported by any of {_readers()}")


def get_reader_for_path(path):
    """Return a reader class for file `path`.

    Raises
    ------
    ValueError
        If no reader class matches.

    See also
    --------
    BaseReader.suffixes
    """
    suffix = Path(path).suffix
    for cls in READERS:
        if cls.supports_suffix(suffix):
            return cls

    raise ValueError(f"File suffix {repr(suffix)} not supported by any of {_readers()}")


def read_sdmx(filename_or_obj, format=None, **kwargs):
    """Load a SDMX-ML or SDMX-JSON message from a file or file-like object.

    Parameters
    ----------
    filename_or_obj : str or :class:`~os.PathLike` or file
    format : 'XML' or 'JSON', optional

    Other Parameters
    ----------------
    dsd : :class:`DataStructureDefinition <.BaseDataStructureDefinition>`
        For “structure-specific” `format`=``XML`` messages only.
    """
    reader = None

    try:
        path = Path(filename_or_obj)

        # Open the file
        obj = open(path, "rb")
    except TypeError:
        # Not path-like → opened file
        path = None
        obj = filename_or_obj

    if path:
        try:
            # Use the file extension to guess the reader
            reader = get_reader_for_path(filename_or_obj)
        except ValueError:
            pass

    if not reader:
        try:
            reader = get_reader_for_path(Path(f"dummy.{format.lower()}"))
        except (AttributeError, ValueError):
            pass

    if not reader:
        # Read a line and then return the cursor to the initial position
        pos = obj.tell()
        first_line = obj.readline().strip()
        obj.seek(pos)

        try:
            reader = detect_content_reader(first_line)
        except ValueError:
            pass

    if not reader:
        raise RuntimeError(
            f"cannot infer SDMX message format from path {repr(path)}, "
            f"format={format}, or content '{first_line[:5].decode()}..'"
        )

    return reader().read_message(obj, **kwargs)
