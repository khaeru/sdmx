import io
import logging
import pathlib
from functools import lru_cache
from typing import TYPE_CHECKING, Any, ClassVar, Optional
from warnings import warn

import requests

from sdmx.format import MediaType

if TYPE_CHECKING:
    import sdmx.message
    import sdmx.model.common

log = logging.getLogger(__name__)


class Converter:
    """Base class for conversion to :mod:`sdmx` objects."""

    @classmethod
    def handles(cls, data: Any, kwargs: dict) -> bool:
        """Return :any:`True` if the class can convert `data` using `kwargs`."""
        return False

    def convert(self, data: Any, **kwargs) -> "sdmx.message.Message":
        """Convert `data` to an instance of an SDMX Message subclass."""
        raise NotImplementedError


class BaseReader(Converter):
    """Converter of file or binary data in standard SDMX formats."""

    #: First byte(s) of file or response body content, used by
    #: :meth:`~.BaseReader.handles`.
    binary_content_startswith: ClassVar[Optional[bytes]] = None

    #: List of media types, used by :meth:`.handles`.
    media_types: ClassVar[list[MediaType]] = []

    #: List of file name suffixes, used by :meth:`.handles`.
    suffixes: ClassVar[list[str]] = []

    @classmethod
    def detect(cls, content: bytes) -> bool:
        """Detect whether the reader can handle `content`.

        .. deprecated:: 2.20.0
           Use :meth:`~.BaseReader.handles` instead.

        Returns
        -------
        bool
            :obj:`True` if the reader can handle the content.
        """
        warn(
            "BaseReader.detect(bytes); use Converter.handles() instead",
            DeprecationWarning,
        )
        return False

    @classmethod
    @lru_cache()
    def handles_media_type(cls, value: str) -> bool:
        """:obj:`True` if the reader can handle content/media type `value`.

        .. deprecated:: 2.20.0
           Use :meth:`~.BaseReader.handles` instead.
        """
        warn(
            "BaseReader.handles_media_type(str); use Converter.handles(requests.Response) instead",
            DeprecationWarning,
        )
        for mt in cls.media_types:
            if mt.match(value):
                return True
        return False

    @classmethod
    def supports_suffix(cls, value: str) -> bool:
        """:obj:`True` if the reader can handle files with suffix `value`.

        .. deprecated:: 2.20.0
           Use :meth:`~.BaseReader.handles` instead.
        """
        warn(
            "BaseReader.supports_suffix(str); use Converter.handles(pathlib.Path) instead",
            DeprecationWarning,
        )
        return cls.handles(pathlib.Path(f"_.{value.lower()}"), {})

    @classmethod
    def handles(cls, data, kwargs):
        """Return :any:`True` if the Reader can convert `data` using `kwargs`.

        The default implementation checks for any of the following conditions:

        1. `data` is :class:`pathlib.Path` and has one of the Reader's
           :attr:`.suffixes`. The match is case-insensitive.
        2. `data` is :class:`requests.Response` and its
           :attr:`~requests.Response.headers` include a ``content-type`` that is matched
           by one of the :class:`.MediaTypes` in the Reader' :attr:`.media_types`.
        3. `data` is :class:`bytes`, :class:`io.IOBase`, or :class:`io.BufferedReader`
           and starts with the class' :attr:`.binary_content_startswith` (if any). For
           the :mod:`io` classes, this check is performed by 'peeking' at the content
           without changing the position in the file for a later call to
           :meth:`.convert`.
        """
        if isinstance(data, pathlib.Path):
            # `data` is a Path with a known suffix
            # Formerly supports_suffix()
            return data.suffix.lower() in cls.suffixes
        elif isinstance(data, requests.Response):
            # `data` is a HTTP Response with given content-type headers
            # Formerly handles_media_type()
            value = data.headers.get("content-type", "")
            return any(mt.match(value) for mt in cls.media_types)
        elif bcsw := cls.binary_content_startswith:
            if isinstance(data, bytes):
                # `data` is raw bytes
                # Formerly detect()
                peek = data
            elif isinstance(data, io.BufferedReader):
                # `data` is a subtype of io.IOBase that supports peek()
                peek = data.peek(len(bcsw))
            elif isinstance(data, io.IOBase):
                # `data` is a subtype of io.IOBase that supports tell()/seek()
                # Formerly in read_sdmx()
                pos = data.tell()
                peek = data.readline().strip()
                data.seek(pos)  # Return to original `pos`ition
            else:
                peek = b""

            return peek.startswith(bcsw)

        return False

    def convert(
        self, data, structure: Optional["sdmx.model.common.Structure"] = None, **kwargs
    ):
        """Convert `data` to an instance of an SDMX Message subclass.

        Parameters
        ----------
        data : file-like
            Message content.
        structure :
            :class:`DataStructure <.BaseDataStructureDefinition>` or
            :class:`MetadataStructure <.BaseMetadataStructureDefinition>`
            for aid in reading `source`.

        Returns
        -------
        :class:`.Message`
            An instance of a Message subclass.
        """
        raise NotImplementedError

    def read_message(self, *args, **kwargs):
        """Deprecated. Use :meth:`.convert` instead."""
        warn(
            "Reader.read_message(); use Converter.convert() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.convert(*args, **kwargs)

    @classmethod
    def _handle_deprecated_kwarg(
        cls, structure: Optional["sdmx.model.common.Structure"], kwargs
    ) -> Optional["sdmx.model.common.Structure"]:
        try:
            dsd = kwargs.pop("dsd")
        except KeyError:
            dsd = None
        else:
            warn(
                "Reader.read_message(…, dsd=…) keyword argument; use structure=…",
                DeprecationWarning,
                stacklevel=2,
            )
            if structure and structure is not dsd:
                raise ValueError(f"Mismatched structure={structure}, dsd={dsd}")
        return structure or dsd
