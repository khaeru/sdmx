import logging

from . import Source as BaseSource

log = logging.getLogger(__name__)


class Source(BaseSource):
    """Work around non-standard behaviour of the :ref:`BBK` web service."""

    _id = "BBK"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._base_url = self.url

    def modify_request_args(self, kwargs):
        super().modify_request_args(kwargs)

        if kwargs["resource_type"] != "data":
            # Construct the URL: insert "/metadata"
            self.url = self._base_url + "/metadata"

            # Omit the version part of the URL
            kwargs.setdefault("version", "")
            if kwargs["version"] != "":
                log.warning(
                    f"URL part version={kwargs['version']} not supported; discarded"
                )
                kwargs["version"] = ""
        else:
            self.url = self._base_url
