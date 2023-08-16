import ssl
from typing import TYPE_CHECKING

import requests.adapters

if TYPE_CHECKING:
    import sdmx.client


class HTTPSAdapter(requests.adapters.HTTPAdapter):
    """:class:`~requests.adapters.HTTPAdapter` with custom :class:`~.ssl.SSLContext`."""

    def __init__(self, ssl_context=None, **kwargs):
        # Per https://stackoverflow.com/a/71646353/: create a context with the flag
        # OP_LEGACY_SERVER_CONNECT set
        self.ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        self.ssl_context.options |= 0x4

        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False):
        import urllib3.poolmanager

        self.poolmanager = urllib3.poolmanager.PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=self.ssl_context,
        )


def Client(*args, **kwargs) -> "sdmx.client.Client":
    """Work around OECD_JSON legacy SSL issues.

    As of 2023-08-16 the OECD_JSON data source uses an old, insecure version of SSL/TLS
    that—with default SSL configuration on properly patched systems—raises a
    :class:`~requests.exceptions.SSLError` “UNSAFE_LEGACY_RENEGOTIATION_DISABLED”.

    This function creates a :class:`.Client` using the workaround described at
    https://stackoverflow.com/a/71646353/ to allow connecting to this data source.

    .. warning::

       Using this workaround disables SSL configuration that is intended to mitigate
       against man-in-the-middle attacks as described in `CVE-2009-3555
       <https://cve.mitre.org/cgi-bin/cvename.cgi?name=CAN-2009-3555>`__. Use with
       caution: in particular, do not change the :attr:`.Source.url` to use with data
       sources other than OECD_JSON.
    """
    import sdmx.client

    # Create a client
    client = sdmx.client.Client(*args, **kwargs)
    # Mount the adapter on the client's Session object
    client.session.mount("https://", HTTPSAdapter())

    return client
