from .oecd import Source as OECD


class Source(OECD):
    _id = "OECD3"

    def modify_request_args(self, kwargs):
        """Supply explicit agency ID for OECD3.

        This hook sets the agency_id to "*" for structure queries if it is not given
        explicitly. This avoids that the (package-specific) source ID "OECD3" is used.
        """
        super().modify_request_args(kwargs)

        # NB this is an indirect test for resource_type != 'data'; because of the way
        #    the hook is called, resource_type is not available directly.
        if "key" not in kwargs:
            kwargs.setdefault("agency_id", "*")
