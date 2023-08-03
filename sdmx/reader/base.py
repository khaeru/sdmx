import logging
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import List

from sdmx.format import MediaType

log = logging.getLogger(__name__)


class BaseReader(ABC):
    #: List of media types handled by the reader.
    media_types: List[MediaType] = []

    #: List of file name suffixes handled by the reader.
    suffixes: List[str] = []

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
    def read_message(self, source, dsd=None):
        """Read message from *source*.

        Parameters
        ----------
        source : file-like
            Message content.
        dsd : :class:`DataStructureDefinition <.BaseDataStructureDefinition>`, optional
            DSD for aid in reading `source`.

        Returns
        -------
        :class:`.Message`
            An instance of a Message subclass.
        """
        pass  # pragma: no cover
