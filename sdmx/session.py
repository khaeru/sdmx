from io import BufferedIOBase, BufferedRandom, BytesIO
from operator import itemgetter
from typing import IO, TYPE_CHECKING, Union

from sdmx.util import HAS_REQUESTS_CACHE, MaybeCachedSession

if TYPE_CHECKING:
    import os

#: Known keyword arguments for requests_cache.CachedSession.
CACHE_KW = [
    "allowable_codes",
    "allowable_methods",
    "backend",
    "cache_name",
    "expire_after",
    "extension",
    "fast_save",
    "location",
    "old_data_on_error",
]


class Session(metaclass=MaybeCachedSession):
    """:class:`requests.Session` subclass with optional caching.

    If :mod:`requests_cache` is installed, this class inherits from
    :class:`~.requests_cache.CachedSession` and caches responses.

    Parameters
    ----------
    timeout : float
        Timeout in seconds, used for every request.

    Other parameters
    ----------------
    kwargs :
        Values for any attributes of :class:`requests.Session`, e.g.
        :attr:`~requests.Session.proxies`,
        :attr:`~requests.Session.stream`, or
        :attr:`~requests.Session.verify`.

    Raises
    ------
    TypeError
        if :mod:`requests_cache` is *not* installed and any parameters are passed.

    """

    def __init__(self, timeout=30.1, **kwargs):
        # Separate keyword arguments for CachedSession
        cache_kwargs = dict(
            filter(itemgetter(1), [(k, kwargs.pop(k, None)) for k in CACHE_KW])
        )

        if HAS_REQUESTS_CACHE:
            # Using requests_cache.CachedSession

            # No cache keyword arguments supplied = don't use the cache
            disabled = not len(cache_kwargs.keys())

            if disabled:
                # Avoid creating any file
                cache_kwargs.setdefault("backend", "memory")

            super(Session, self).__init__(**cache_kwargs)

            # Overwrite value from requests_cache.CachedSession.__init__()
            self._is_cache_disabled = disabled
        elif len(cache_kwargs):  # pragma: no cover
            raise TypeError(
                "Arguments not supported without requests_session installed: "
                + repr(cache_kwargs)
            )
        else:  # pragma: no cover
            # Plain requests.Session: no arguments
            super(Session, self).__init__()

        # Store timeout; not a property of requests.Session
        self.timeout = timeout

        # Addition keyword arguments must match existing attributes of requests.Session
        for name, value in kwargs.items():
            if hasattr(self, name):
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
