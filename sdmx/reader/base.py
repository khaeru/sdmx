import logging
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import TYPE_CHECKING, ClassVar, Optional
from warnings import warn

from sdmx.format import MediaType

if TYPE_CHECKING:
    import sdmx.model.common

log = logging.getLogger(__name__)


class BaseReader(ABC):
    #: List of media types handled by the reader.
    media_types: ClassVar[list[MediaType]] = []

    #: List of file name suffixes handled by the reader.
    suffixes: ClassVar[list[str]] = []

    @classmethod
    def detect(cls, content: bytes) -> bool:
        """Detect whether the reader can handle `content`.

        Returns
        -------
        bool
            :obj:`True` if the reader can handle the content.
        """
        return False

    @classmethod
    @lru_cache()
    def handles_media_type(cls, value: str) -> bool:
        """:obj:`True` if the reader can handle content/media type `value`."""
        for mt in cls.media_types:
            if mt.match(value):
                return True
        return False

    @classmethod
    def supports_suffix(cls, value: str) -> bool:
        """:obj:`True` if the reader can handle files with suffix `value`."""
        return value.lower() in cls.suffixes

    @abstractmethod
    def read_message(
        self,
        source,
        structure: Optional["sdmx.model.common.Structure"] = None,
        **kwargs,
    ):
        """Read message from *source*.

        Parameters
        ----------
        source : file-like
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
        pass  # pragma: no cover

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
