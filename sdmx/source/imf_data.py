from . import Source as BaseSource


class Source(BaseSource):
    """Hooks for the ``IMF_DATA`` SDMX-REST API."""

    _id = "IMF_DATA"

    def modify_request_args(self, kwargs):
        """Modify arguments used to build query URL.

        Set default provider agency ID ``all``.
        """
        super().modify_request_args(kwargs)

        # Supply 'all' as the default agency_id
        # NB this is an indirect test for resource_type != 'data'; because of the way
        #    the hook is called, resource_type is not available directly.
        if "key" not in kwargs:
            kwargs.setdefault("agency_id", "all")
