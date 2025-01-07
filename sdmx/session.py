from io import BufferedIOBase, BufferedRandom, BytesIO
from typing import IO, TYPE_CHECKING, Union

import requests

from sdmx.util.requests import HAS_REQUESTS_CACHE, CacheMixin, SessionAttrs

if TYPE_CHECKING:
    import os


class Session(CacheMixin, requests.Session):
    """:class:`requests.Session` with optional caching.

    If :mod:`requests_cache` is installed, this class inherits from
    :class:`~.requests_cache.CacheMixin` and caches responses. Otherwise, it inherits
    only from the :class:`requests_cache`.

    Parameters
    ----------
    timeout : float
        Timeout in seconds, used for every request.

    Other parameters
    ----------------
    kwargs :
        These may include:

        1. Values for any attributes of :class:`requests.Session`, such as
           :attr:`~requests.Session.proxies`,
           :attr:`~requests.Session.stream`, or
           :attr:`~requests.Session.verify`. These are set on the created Session.
        2. Keyword arguments to :class:`~.requests_cache.CacheMixin` or any
           :mod:`requests_cache` backend. Note that:

           - Unlike :mod:`requests_cache`, you must supply :py:`backend="sqlite"`
             explicitly; otherwise :mod:`sdmx` uses :py:`backend="memory"`.
           - These classes will silently ignore any other/unrecognized keyword
             arguments.

    Raises
    ------
    TypeError
        if :mod:`requests_cache` is *not* installed and any parameters are passed except
        for `timeout`.
    """

    timeout: float

    def __init__(self, timeout: float = 30.0, **kwargs):
        # Store timeout; not an attribute of requests.Session
        self.timeout = timeout

        # Separate kwargs that will update base requests.Session attributes
        attrs = [
            (k, kwargs.pop(k)) for k in set(SessionAttrs.__annotations__) & set(kwargs)
        ]

        if HAS_REQUESTS_CACHE:
            # Disable caching entirely if no cache-related kwargs are supplied
            kwargs.setdefault("disabled", not len(kwargs))
            kwargs.setdefault("backend", "memory")  # Avoid creating any file
        elif len(kwargs):  # pragma: no cover
            raise TypeError(
                f"Keyword arguments for not installed requests_cache: {kwargs}"
            )

        super().__init__(**kwargs)

        # Update attributes set by requests.Session.__init__()
        for name, value in attrs:
            setattr(self, name, value)


class ResponseIO(BufferedIOBase):
    """Buffered wrapper for :class:`requests.Response` with optional file output.

    :class:`ResponseIO` wraps a :class:`requests.Response` object's 'content'
    attribute, providing a file-like object from which bytes can be :meth:`read`
    incrementally.

    Parameters
    ----------
    response : :class:`requests.Response`
        HTTP response to wrap.
    tee : binary, writable :py:class:`io.BufferedIOBase`, defaults to io.BytesIO()
        *tee* is exposed as *self.tee* and not closed explicitly.
    """

    tee: IO

    def __init__(self, response, tee: Union[IO, "os.PathLike", None] = None):
        self.response = response

        if tee is None:
            self.tee = BytesIO()
        elif isinstance(tee, (IO, BufferedRandom)):
            # If tee is a file-like object or tempfile, then use it as cache
            self.tee = tee
        else:
            # So tee must be str, pathlib.Path, or similar
            self.tee = open(tee, "w+b")

        content_disposition = response.headers.get("Content-Disposition", "")
        if content_disposition.endswith('.gz"'):
            import gzip

            content = gzip.GzipFile(fileobj=BytesIO(response.content)).read()
        else:
            content = response.content

        self.tee.write(content)
        self.tee.seek(0)

    def readable(self):
        return True

    def read(self, size=-1):
        """Read and return up to `size` bytes by calling ``self.tee.read()``."""
        return self.tee.read(size)
