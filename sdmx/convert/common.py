from collections.abc import Callable
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


class DispatchConverter(Converter):
    """Base class for recursive converters.

    Usage:

    - Create an instance of this class.
    - Use :meth:`register` (in the same manner as Python's built-in
      :func:`functools.singledispatch`) to decorate functions that convert certain types
      of :mod:`sdmx.model` or :mod:`sdmx.message` objects.
    - Call :meth:`recurse` to kick off recursive writing of objects, including from
      inside other functions.

    Example
    -------
    >>> MyWriter = BaseWriter('my')

    >>> @MyWriter.register
    >>> def _(obj: sdmx.model.ItemScheme):
    >>>     ... code to write an ItemScheme ...
    >>>     return result

    >>> @MyWriter.register
    >>> def _(obj: sdmx.model.Codelist):
    >>>     ... code to write a Codelist ...
    >>>     return result
    """

    _registry: dict[type, Callable]

    def convert(self, obj, **kwargs):
        # Use either type(obj) or a parent type to retrieve a conversion function
        for i, cls in enumerate(type(obj).mro()):
            try:
                func = self._registry[cls]
            except KeyError:
                continue
            else:
                if i:  # Some superclass of type(obj) matched → cache for future calls
                    self._registry[type(obj)] = func
                break

        return func(self, obj, **kwargs)

    @classmethod
    def register(cls, func):
        try:
            registry = getattr(cls, "_registry")
        except AttributeError:
            # First call → registry does not exist → create it
            registry = dict()
            setattr(cls, "_registry", registry)

        # Register `func` for the class of the `obj` argument
        registry[getattr(func, "__annotations__")["obj"]] = func

        return func
