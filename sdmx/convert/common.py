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

    - Create a subclass of this class.
    - Use :meth:`register` (in the same manner as Python's built-in
      :func:`functools.singledispatch`) to decorate functions that convert certain types
      of :mod:`sdmx.model` or :mod:`sdmx.message` objects.
    - Call :meth:`convert` (including from inside other functions) to recursively
      convert objects.

    Example
    -------
    >>> from sdmx.convert.common import DispatchConverter
    >>> class CustomConverter(DispatchConverter):
    ...     pass

    >>> @CustomConverter.register
    ... def _(c: "CustomConverter", obj: sdmx.model.ItemScheme):
    ...     ... code to convert an ItemScheme ...
    ...     return result

    >>> @CustomConverter.register
    ... def _(c: "CustomConverter", obj: sdmx.model.Codelist):
    ...     ... code to convert a Codelist ...
    ...     return result
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

        try:
            return func(self, obj, **kwargs)
        except UnboundLocalError:  # pragma: no cover
            raise NotImplementedError(
                f"Convert {type(obj)} using {type(self).__name__}"
            ) from None

    @classmethod
    def register(cls, func: "Callable"):
        """Register `func` as a conversion function.

        `func` must have an argument named `obj` that is annotated with a particular
        type.
        """
        try:
            registry = getattr(cls, "_registry")
        except AttributeError:
            # First call → registry does not exist → create it
            registry = dict()
            setattr(cls, "_registry", registry)

        # Register `func` for the class of the `obj` argument
        registry[getattr(func, "__annotations__")["obj"]] = func

        return func
