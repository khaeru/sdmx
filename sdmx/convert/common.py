from typing import Any


class Converter:
    """Base class for conversion to or from :mod:`sdmx` objects."""

    @classmethod
    def handles(cls, data: Any, kwargs: dict) -> bool:
        """Return :any:`True` if the class can convert `data` using `kwargs`."""
        return False

    def convert(self, data: Any, **kwargs) -> Any:
        """Convert `data`."""
        raise NotImplementedError
