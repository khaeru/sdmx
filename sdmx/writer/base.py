from functools import singledispatch


class NoWriterImplementation(NotImplementedError):
    pass


class BaseWriter:
    """Base class for recursive writers.

    Usage:

    - Create an instance of this class.
    - Use :meth:`register` in the same manner as Python's built-in
      :func:`functools.singledispatch` to decorate functions that certain types of
      :mod:`sdmx.model` or :mod:`sdmx.message` objects.
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

    def __init__(self, format_name):
        # Create the single-dispatch function
        @singledispatch
        def func(obj, *args, **kwargs):
            raise NoWriterImplementation(f"write {type(obj).__name__} to {format_name}")

        self._dispatcher = func

    def recurse(self, obj, *args, **kwargs):
        """Recursively write *obj*.

        If there is no :meth:`register` 'ed function to write the class of `obj`, then
        the parent class of `obj` is used to find a method.
        """
        dispatcher = getattr(self, "_dispatcher")

        try:
            # Let the single dispatch function choose the overload
            return dispatcher(obj, *args, **kwargs)
        except NoWriterImplementation as exc:
            try:
                # Use the object's parent class to get a different implementation
                cls = type(obj).mro()[1]
                func = dispatcher.registry[cls]
            except KeyError:
                raise exc  # No implementation for the parent class
            else:
                # Success; register the function so it is found directly next time
                dispatcher.register(type(obj), func)

            return func(obj, *args, **kwargs)

    def __call__(self, func):
        """Register *func* as a writer for a particular object type."""
        dispatcher = getattr(self, "_dispatcher")
        dispatcher.register(func)
        return func
