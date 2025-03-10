from requests.structures import CaseInsensitiveDict

from sdmx.format import MediaType

from . import Source as BaseSource


class Source(BaseSource):
    """Hooks for the ``IMF_DATA3`` SDMX-REST API."""

    _id = "IMF_DATA3"

    def modify_request_args(self, kwargs):
        """Modify arguments used to build query URL.

        1. Set default provider agency ID ``all``.
        2. Set media-type in header.
        """
        super().modify_request_args(kwargs)

        # Supply 'all' as the default agency_id
        # NB this is an indirect test for resource_type != 'data'; because of the way
        #    the hook is called, resource_type is not available directly.
        if "key" not in kwargs:
            kwargs.setdefault("agency_id", "all")

        # Retrieve SDMX-ML by default
        # TODO Choose between the data, metadata, or structure media-type according to
        #      other `kwargs`
        kwargs.setdefault("headers", CaseInsensitiveDict())
        mt = [MediaType(x, "xml", "3.0.0") for x in ("data", "metadata", "structure")]
        kwargs["headers"].setdefault("Accept", ", ".join(map(str, mt)))
