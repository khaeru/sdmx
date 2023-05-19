from .estat import Source as ESTAT


class Source(ESTAT):
    _id = "ESTAT_COMEXT"

    def modify_request_args(self, kwargs):
        """Supply explicit provider agency ID for ESTAT_COMEXT.

        This hook sets the provider to "ESTAT" for structure queries if it is not given
        explicitly.
        """
        super().modify_request_args(kwargs)

        # NB this is an indirect test for resource_type != 'data'; because of
        #    the way the hook is called, resource_type is not available
        #    directly.
        if "key" not in kwargs:
            kwargs.setdefault("provider", "ESTAT")
