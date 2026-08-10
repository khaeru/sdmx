from sdmx.rest import Resource
from sdmx.source import Source as BaseSource


class Source(BaseSource):
    _id = "WB_WDI"

    def modify_request_args(self, kwargs):
        """World Bank's agency ID."""
        super().modify_request_args(kwargs)

        if kwargs.get("resource_type") == Resource.categoryscheme:
            # Service does not respond to requests for "WB" category schemes
            kwargs["provider"] = "all"
        elif kwargs.get("resource_type") == Resource.data:
            # Provider's own ID differs from its ID in this package
            kwargs.setdefault("provider", "WB")
        elif kwargs.get("resource_type") == Resource.dataflow:
            # Here we have no agency_id (/all/latest is allowed).
            # Unless set, it is added automatically, use url to avoid that.
            kwargs.pop("resource_type")
            if not all(value is None for value in kwargs.values()):
                raise ValueError(
                    "WDI dataflow is a unique endpoint and doesn't support arguments"
                )
            kwargs.setdefault(
                "url", "https://api.worldbank.org/v2/sdmx/rest/dataflow"
            )
        elif kwargs.get("resource_type") in {Resource.datastructure, Resource.codelist}:
            # Here /all/latest is not allowed.
            # It is added automatically, use url to circumvent that.
            name = kwargs.get("resource_type").name
            kwargs.pop("resource_type")
            if not all(value is None for value in kwargs.values()):
                raise ValueError(
                    f"WDI {name} is a unique endpoint and doesn't support arguments"
                )
            kwargs.setdefault("url", f"https://api.worldbank.org/v2/sdmx/rest/{name}/wb")

        try:
            if isinstance(kwargs["key"], str):
                # Data queries fail without a trailing slash
                # TODO improve the hook integration with Client.get so this can be done
                #      after the query URL is prepared
                kwargs["key"] += "/"
        except KeyError:
            pass
