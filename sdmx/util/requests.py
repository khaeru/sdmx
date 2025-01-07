"""Utilities for working with :mod:`requests` and related packages."""

from typing import TYPE_CHECKING, Optional, TypedDict, Union

import urllib3
from requests import PreparedRequest, Response
from requests.adapters import BaseAdapter

#: :any:`True` if :class:`requests_cache` is installed.
HAS_REQUESTS_CACHE = True

try:
    from requests_cache import CacheMixin

except ImportError:  # pragma: no cover
    HAS_REQUESTS_CACHE = False

    class CacheMixin:  # type: ignore [no-redef]
        """Null parent class for sdmx.session.Session."""


if TYPE_CHECKING:
    import http.cookiejar

    from requests_cache import CachedSession


__all__ = [
    "HAS_REQUESTS_CACHE",
    "CacheMixin",
    "OfflineAdapter",
    "SessionAttrs",
    "offline",
    "save_response",
]


class OfflineAdapter(BaseAdapter):
    """A request Adapter that raises :class:`RuntimeError` for every request.

    See also
    --------
    offline
    """

    def send(self, request, **kwargs):
        raise RuntimeError(f"Attempted query in offline mode for URL:\n{request.url}")


class SessionAttrs(TypedDict):
    """Attributes of :class:`.requests.Session`.

    These are not available from :mod:`requests` itself, thus recorded here for use in
    :meth:`sdmx.session.Session.__init__`.
    """

    adapters: dict
    auth: Optional[object]
    cert: Union[str, tuple[str, str]]
    cookies: "http.cookiejar.CookieJar"
    headers: dict
    hooks: dict
    max_redirects: int
    params: dict
    proxies: dict
    stream: bool
    trust_env: bool
    verify: bool


def offline(s) -> None:
    """Make session `s` behave as if offline.

    Replace all of the :attr:`Session.adapters` of `s` with instances of
    :class:`OfflineAdapter`. This has the effect that any request made through `s` that
    is not handled in some other way (for instance, by :mod:`requests_cache`) will raise
    :class:`RuntimeError`.
    """
    a = OfflineAdapter()
    for k in s.adapters.keys():
        s.adapters[k] = a


def save_response(
    session: "CachedSession", method: str, url: str, content: bytes, headers: dict
) -> None:
    """Store a response in the cache of `session`."""
    # Response object and its direct attributes
    resp = Response()
    resp._content = content
    resp.status_code = 200
    resp.headers.update(headers)
    resp.url = url

    # Subsidiary objects: 'raw' (urllib3) response
    resp.raw = urllib3.HTTPResponse(request_url=url)

    # PreparedRequest
    req = resp.request = PreparedRequest()
    req.prepare(method=method, url=url)

    session.cache.save_response(resp)
