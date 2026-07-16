import re

from requests.structures import CaseInsensitiveDict

from sdmx.rest import Resource

from . import Source as BaseSource

re_500 = re.compile(r"(An error has occurred)\.")


class Source(BaseSource):
    _id = "ABS"

    def modify_request_args(self, kwargs):
        """Request ABS structural metadata explicitly as SDMX-ML."""
        super().modify_request_args(kwargs)

        if kwargs.get("resource_type") is Resource.data:
            return

        headers = CaseInsensitiveDict(kwargs.get("headers", {}))
        headers.setdefault("Accept", "application/xml")
        kwargs["headers"] = headers

    def handle_response(self, response, content):
        """Handle ABS' own text/html error page for some endpoints."""
        ctype = response.headers.get("content-type", "")
        if "text/html" in ctype:
            buf = ""
            while True:
                chunk = content.read().decode()
                if len(chunk) == 0:
                    break

                buf += chunk

                match = re_500.search(buf)
                if match:
                    # Overwrite the original response
                    (response.reason,) = match.groups()
                    response.status_code = 500
                    response.raise_for_status()

        return super().handle_response(response, content)
