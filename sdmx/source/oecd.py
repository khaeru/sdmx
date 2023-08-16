from . import Source as BaseSource


class Source(BaseSource):
    _id = "OECD"

    def modify_request_args(self, kwargs):
        """Supply explicit provider agency ID for OECD.

        The structures and data flows from this provider use a variety of agency IDs—for
        example “OECD.SDD.TPS”—to identify a specific the organizational unit within the
        OECD that is responsible for each object. Queries requesting structures or data
        with agency ID “OECD” (strictly) may return few or zero results.

        This hook sets the provider to “ALL” for structure queries if it is not given
        explicitly.
        """
        super().modify_request_args(kwargs)

        # NB this is an indirect test for resource_type != 'data'; because of the way
        #    the hook is called, resource_type is not available directly.
        if "key" not in kwargs:
            kwargs.setdefault("provider", "ALL")
