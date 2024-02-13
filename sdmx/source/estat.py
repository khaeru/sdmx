import logging
from tempfile import NamedTemporaryFile
from time import sleep
from typing import Dict
from urllib.parse import urlparse
from zipfile import ZipFile

import requests

from sdmx.rest import Resource
from sdmx.source import Source as BaseSource

log = logging.getLogger(__name__)


def handle_references_param(kwargs: Dict) -> None:
    """Handle the "references" query parameter for ESTAT and similar.

    For this parameter, the server software behind ESTAT's data source only supports
    (as of 2022-11-13) the values "children", "descendants", or "none". Other values—
    including the "all" or parentsandsiblings" used as defaults by :class:`.Client`—
    result in error messages.

    This handler, used via :meth:`.Source.modify_request_args`:

    - Replaces the defaults of "all" or "parentsandsiblings" set by :class:`.Client`
      with "descendants".
    - Replaces other, unsupported values with "none".
    """
    try:
        resource_type = kwargs.get("resource_type") or Resource.from_obj(
            kwargs["resource"]
        )
    except KeyError:
        resource_type = None
    resource_id = kwargs.get("resource_id") or getattr(
        kwargs.get("resource", None), "id", None
    )
    params = kwargs.setdefault("params", {})

    # Preempt default values that would be set by Client._request_from_args()
    if not params.get("references"):
        if resource_type == Resource.datastructure and resource_id:
            params["references"] = "descendants"
        elif (
            resource_type == Resource.dataflow and resource_id
        ) or resource_type == Resource.categoryscheme:
            params["references"] = "descendants"

    # Replace unsupported values
    references = params.get("references")
    if references not in ("children", "descendants", "none", None):
        log.info(f"Replace unsupported references={references!r} with 'none'")
        params["references"] = "none"


class Source(BaseSource):
    """Handle Eurostat's mechanism for large datasets and other quirks.

    For some requests, ESTAT returns a DataMessage that has no content except for a
    ``<footer:Footer>`` element containing a URL where the data will be made available
    as a ZIP file.

    To configure :meth:`finish_message`, pass its `get_footer_url` argument to
    :meth:`.Client.get`.

    .. versionadded:: 0.2.1
    """

    _id = "ESTAT"

    def modify_request_args(self, kwargs):
        """Modify arguments used to build query URL.


        See also
        --------
        :pull:`107`, :pull:`108`
        """
        super().modify_request_args(kwargs)

        kwargs.pop("get_footer_url", None)

        handle_references_param(kwargs)

    def finish_message(self, message, request, get_footer_url=(30, 3), **kwargs):
        """Handle the initial response.

        This hook identifies the URL in the footer of the initial response,
        makes a second request (polling as indicated by *get_footer_url*), and
        returns a new DataMessage with the parsed content.

        Parameters
        ----------
        get_footer_url : (int, int)
            Tuple of the form (`seconds`, `attempts`), controlling the interval
            between attempts to retrieve the data from the URL, and the
            maximum number of attempts to make.
        """
        # Check the message footer for a text element that is a valid URL
        url = None
        for text in getattr(message.footer, "text", []):
            if urlparse(str(text)).scheme:
                url = str(text)
                break

        if not url:
            return message

        # Unpack arguments
        wait_seconds, attempts = get_footer_url

        # Create a temporary file to store the ZIP response
        ntf = NamedTemporaryFile(prefix="sdmx-")
        # Make a limited number of attempts to retrieve the file
        for a in range(attempts):
            sleep(wait_seconds)
            try:
                # This line succeeds if the file exists; the ZIP response is stored to
                # ntf, and then used by the handle_response() hook below
                return request.get(url=url, tofile=ntf.file)
            except requests.HTTPError:
                raise
        ntf.close()
        raise RuntimeError("Maximum attempts exceeded")

    def handle_response(self, response, content):
        """Handle the polled response.

        The request for the indicated ZIP file URL returns an octet-stream;
        this handler saves it, opens it, and returns the content of the single
        contained XML file.
        """

        if response.headers["content-type"] != "application/octet-stream":
            return response, content

        # Read all the input, forcing it to be copied to
        # content.tee_filename
        while True:
            if len(content.read()) == 0:
                break

        # Open the zip archive
        with ZipFile(content.tee, mode="r") as zf:
            # The archive should contain only one file
            infolist = zf.infolist()
            assert len(infolist) == 1

            # Set the new content type
            response.headers["content-type"] = "application/xml"

            # Use the unzipped archive member as the response content
            return response, zf.open(infolist[0])
