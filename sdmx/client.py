import logging
from functools import partial
from typing import IO, TYPE_CHECKING, Any, Dict, Optional, Union
from warnings import warn

import requests

from sdmx.model import common
from sdmx.model.v21 import DataStructureDefinition
from sdmx.reader import get_reader_for_media_type
from sdmx.rest import Resource
from sdmx.session import ResponseIO, Session
from sdmx.source import NoSource, list_sources, sources

if TYPE_CHECKING:
    import io
    import os

    import sdmx.message
    import sdmx.source

log = logging.getLogger(__name__)


def Request(*args, **kwargs):
    """Compatibility function for :class:`Client`.

    .. versionadded:: 2.0

    .. deprecated:: 2.0
       Will be removed in :mod:`sdmx` version 3.0.

    """
    message = "Request class will be removed in v3.0; use Client(…)"
    log.warning(message)
    warn(message, DeprecationWarning)
    return Client(*args, **kwargs)


class Client:
    """Client for a SDMX REST web service.

    Parameters
    ----------
    source : str or source.Source
        Identifier of a data source. If a string, must be one of the known sources in
        :meth:`list_sources`.
    log_level : int
        Override the package-wide logger with one of the
        :ref:`standard logging levels <py:levels>`.

        .. deprecated:: 2.0
           Will be removed in :mod:`sdmx` version 3.0.
    **session_opts
        Additional keyword arguments are passed to :class:`.Session`.

    """

    cache: Dict[str, "sdmx.message.Message"] = {}

    #: :class:`.source.Source` for requests sent from the instance.
    source: "sdmx.source.Source"

    #: :class:`.Session` for queries sent from the instance.
    session: requests.Session

    # Stored keyword arguments "allow_redirects" and "timeout" for pre-requests.
    _send_kwargs: Dict[str, Any] = {}

    def __init__(self, source=None, log_level=None, **session_opts):
        try:
            self.source = sources[source.upper()] if source else NoSource
        except KeyError:
            raise ValueError(
                f"source must be None or one of: {' '.join(list_sources())}"
            )

        # Create an HTTP Session object to reuse a connection for multiple requests
        self.session = Session(**session_opts)

        if log_level:
            message = "Client(…, log_level=…) parameter"
            log.warning(f"Deprecated: {message}")
            warn(message, DeprecationWarning)
            logging.getLogger("pandasdmx").setLevel(log_level)

    def __getattr__(self, name):
        """Convenience methods."""
        try:
            # Provide resource_type as a positional argument, so that the first
            # positional argument to the convenience method is treated as resource_id
            func = partial(self.get, Resource[name])
        except KeyError:
            raise AttributeError
        else:
            # Modify the docstring to explain the argument fixed by the convenience
            # method
            func.__doc__ = self.get.__doc__.replace(
                ".\n", f" with resource_type={repr(name)}.\n", 1
            )
            return func

    def __dir__(self):
        """Include convenience methods in dir()."""
        return super().__dir__() + [ep.name for ep in Resource]

    def clear_cache(self):
        self.cache.clear()

    @property
    def timeout(self):
        warn(
            "Getting Client.timeout directly; use Client.session.timeout",
            DeprecationWarning,
        )
        return self.session.timeout

    @timeout.setter
    def timeout(self, value):
        warn(
            f"Setting Client.timeout directly; use Client.session.timeout={value}",
            DeprecationWarning,
        )
        self.session.timeout = value

    def series_keys(self, flow_id, use_cache=True):
        """Return all :class:`.SeriesKey` for *flow_id*.

        Returns
        -------
        list
        """
        # download an empty dataset with all available series keys
        return (
            self.data(flow_id, params={"detail": "serieskeysonly"}, use_cache=use_cache)
            .data[0]
            .series.keys()
        )

    def _make_key(self, resource_type, resource_id, key, dsd):
        """Validate `key` if possible.

        If key is :class:`dict`, validate items against `dsd` and construct a query
        string which becomes part of the URL. Otherwise, do nothing, as `key` must be a
        :class:`str` confirming to the REST API spec.
        """
        if not (
            resource_type in (Resource.data, Resource.availableconstraint)
            and isinstance(key, dict)
        ):
            return key, dsd

        # Select validation method based on agency capabilities
        if dsd:
            # DSD was provided
            pass
        elif self.source.supports[Resource.datastructure]:
            # Retrieve the DataStructureDefinition
            dsd = (
                self.dataflow(
                    resource_id, params=dict(references="all"), use_cache=True
                )
                .dataflow[resource_id]
                .structure
            )

            if dsd.is_external_reference:
                # DataStructureDefinition was not retrieved with the Dataflow query;
                # retrieve it explicitly
                dsd = self.get(resource=dsd, use_cache=True).structure[dsd.id]
        else:
            # Construct a DSD from the keys
            dsd = DataStructureDefinition.from_keys(self.series_keys(resource_id))

        # Make a ContentConstraint from the key
        cc = dsd.make_constraint(key)

        return cc.to_query_string(dsd), dsd

    def _request_from_args(self, kwargs):
        """Validate arguments and prepare pieces for a request."""
        headers = kwargs.pop("headers", {})

        # Resource arguments
        resource_type = kwargs.pop("resource_type", None)
        resource_id = kwargs.pop("resource_id", None)

        # Assemble keyword arguments for URL
        kw = dict(
            source=self.source,
            resource_type=resource_type,
            resource_id=resource_id,
            params=kwargs.pop("params", {}),
        )
        if provider := kwargs.pop("provider", None):
            warn("provider= keyword argument; use agency_id", DeprecationWarning, 2)
            kw.update(agency_id=provider)
        if version := kwargs.pop("version", None):
            kw.update(version=version)

        key = kwargs.pop("key", None)
        dsd = kwargs.pop("dsd", None)

        # Pass remaining `kwargs` to URL to either handle or raise
        kw.update(kwargs)
        kwargs.clear()

        if isinstance(key, dict):
            # Make the key, and retain the DSD (if any) for use in parsing
            key, dsd = self._make_key(resource_type, resource_id, key, dsd)
            kwargs["dsd"] = dsd
        elif not (key is None or isinstance(key, str)):
            raise TypeError(f"key must be str or dict; got {key.__class__.__name__}")

        if key is not None:
            kw.update(key=key)

        # Headers: use headers from source config if not given by the caller
        if not headers:
            try:
                headers.update(self.source.headers.get(resource_type.name, {}))
            except AttributeError:
                pass

        # Identify the URL class; handle the `kw`
        # TODO specify API version for sources that support multiple API versions at the
        #      same URL
        url = self.source.get_url_class()(**kw)

        # Allow requests to keep track of the query parameters and rest of the URL
        return requests.Request(
            "get", url.join(with_query=False), params=url.query, headers=headers
        )

    def _request_from_url(self, kwargs):
        url = kwargs.pop("url")
        parameters = kwargs.pop("params", {})
        headers = kwargs.pop("headers", {})

        # kwargs with values other than None are an error
        extra_args = dict(filter(lambda i: i[1] is not None, kwargs.items()))
        if len(extra_args):
            raise ValueError(f"{repr(extra_args)} supplied with get(url=...)")

        return requests.Request("get", url, params=parameters, headers=headers)

    def _handle_get_kwargs(self, kwargs):  # noqa: C901 TODO reduce complexity 12 → ≤11
        if kwargs.pop("validate", None) is not None:
            warn("validate= keyword argument to Client.get()", DeprecationWarning)

        # "resource_type", if given, should be a member of the Resource enum
        if resource_type := kwargs.pop("resource_type", None):
            try:
                resource_type = Resource[resource_type]
            except KeyError:
                raise KeyError(
                    f"resource_type {resource_type!r} not in {Resource.describe()}"
                ) from None
            else:
                kwargs.update(resource_type=resource_type)

        # "resource", if an object is given, should satisfy certain conditions
        if resource := kwargs.pop("resource", None):
            assert isinstance(resource, common.MaintainableArtefact)

            # Class of the object
            resource_type = kwargs.setdefault(
                "resource_type", Resource.from_obj(resource)
            )
            assert kwargs["resource_type"] == Resource.from_obj(resource)

            # ID of the object
            kwargs.update(resource_id=kwargs.get("resource_id") or resource.id)
            assert kwargs["resource_id"] == resource.id, (
                f"mismatch between resource_id={kwargs['resource_id']!r} and "
                f"resource={resource!r}"
            )

        force = kwargs.pop("force", False)
        if resource_type and not (self.source.supports[resource_type] or force):
            raise NotImplementedError(
                f"{self.source.id} does not implement or support the "
                f"{resource_type!r} API endpoint. Use force=True to override"
            )

        # Allow Source class to modify request args
        # TODO this should occur after most processing, defaults, checking etc. are
        #      performed, so that core code does most of the work.
        if self.source:
            self.source.modify_request_args(kwargs)

        def _collect(*keywords):
            return {kw: kwargs.pop(kw) for kw in keywords if kw in kwargs}

        # Update session attributes. These changes persist.
        for name, value in _collect("cert", "proxies", "stream", "verify").items():
            # Log if the new value is different from the old
            old_value = getattr(self.session, name)
            if value != old_value:
                log.debug(f"Client.session.{name}={value} replaces {old_value}")

            # Store
            setattr(self.session, name, value)

        # Separate kwargs for requests.Session.send()
        send_kwargs = _collect("allow_redirects", "timeout")
        if (
            len(send_kwargs)
            and len(self._send_kwargs)
            and send_kwargs != self._send_kwargs
        ):
            log.debug(f"Client.get() args {send_kwargs} replace {self._send_kwargs}")

        self._send_kwargs.update(send_kwargs)

        # Return remaining kwargs
        return kwargs

    def get(
        self,
        resource_type: Union[str, Resource, None] = None,
        resource_id: Optional[str] = None,
        tofile: Union["os.PathLike", IO, None] = None,
        use_cache: bool = False,
        dry_run: bool = False,
        **kwargs,
    ) -> "sdmx.message.Message":
        """Retrieve SDMX data or metadata.

        (Meta)data is retrieved from the :attr:`source` of the current Client. The
        item(s) to retrieve can be specified in one of two ways:

        1. `resource_type`, `resource_id`: These give the type (see :class:`Resource`)
           and, optionally, ID of the item(s). If the `resource_id` is not given, all
           items of the given type are retrieved.
        2. a `resource` object, i.e. a :class:`.MaintainableArtefact`: `resource_type`
           and `resource_id` are determined by the object's class and
           :attr:`id <.IdentifiableArtefact.id>` attribute, respectively.

        Data is retrieved with `resource_type='data'`. In this case, the optional
        keyword argument `key` can be used to constrain the data that is retrieved.
        Examples of the formats for `key`:

        1. ``{'GEO': ['EL', 'ES', 'IE']}``: :class:`dict` with dimension name(s) mapped
           to an iterable of allowable values.
        2. ``{'GEO': 'EL+ES+IE'}``: :class:`dict` with dimension name(s) mapped to
           strings joining allowable values with `'+'`, the logical 'or' operator for
           SDMX web services.
        3. ``'....EL+ES+IE'``: :class:`str` in which ordered dimension values (some
           empty, ``''``) are joined with ``'.'``. Using this form requires knowledge
           of the dimension order in the target data `resource_id`; in the example,
           dimension 'GEO' is the fifth of five dimensions: ``'.'.join(['', '', '', '',
           'EL+ES+IE'])``. :meth:`.CubeRegion.to_query_string` can also be used to
           create properly formatted strings.

        For formats 1 and 2, but not 3, the `key` argument is validated against the
        relevant :class:`DSD <.BaseDataStructureDefinition>`, either given with the
        `dsd` keyword argument, or retrieved from the web service before the main query.

        For the optional `param` keyword argument, some useful parameters are:

        - 'startperiod', 'endperiod': restrict the time range of data to retrieve.
        - 'references': control which item(s) related to a metadata resource are
          retrieved, e.g. `references='parentsandsiblings'`.

        Parameters
        ----------
        resource_type : str or :class:`Resource`, optional
            Type of resource to retrieve.
        resource_id : str, optional
            ID of the resource to retrieve.
        tofile : str or :class:`~os.PathLike` or `file-like object`, optional
            File path or file-like to write SDMX data as it is received.
        use_cache : bool, optional
            If :obj:`True`, return a previously retrieved :class:`~.Message` from
            :attr:`cache`, or update the cache with a newly-retrieved Message.
        dry_run : bool, optional
            If :obj:`True`, prepare and return a :class:`requests.Request` object, but
            do not execute the query. The prepared URL and headers can be examined by
            inspecting the returned object.
        **kwargs
            Other, optional parameters (below).

        Other Parameters
        ----------------
        dsd : :class:`DataStructureDefinition <.BaseDataStructureDefinition>`
            Existing object used to validate the `key` argument. If not provided, an
            additional query executed to retrieve a DSD in order to validate the `key`.
        force : bool
            If :obj:`True`, execute the query even if the :attr:`source` does not
            support queries for the given `resource_type`. Default: :obj:`False`.
        headers : dict
            HTTP headers. Given headers will overwrite instance-wide headers passed to
            the constructor. Default: :obj:`None` to use the default headers of the
            :attr:`source`.
        key : str or dict
            For queries with `resource_type='data'`. :class:`str` values are not
            validated; :class:`dict` values are validated using
            :meth:`~.DataStructureDefinition.make_constraint`.
        params : dict
            Query parameters. The `SDMX REST web service guidelines <https://\
            github.com/sdmx-twg/sdmx-rest/tree/master/v2_1/ws/rest/docs>`_
            describe parameters and allowable values for different queries. `params` is
            not validated before the query is executed.
        provider : str
            ID of the agency providing the data or metadata. Default: ID of the
            :attr:`source` agency.

            An SDMX web service is a ‘data source’ operated by a specific, ‘source’
            agency. A web service may host data or metadata originally published by one
            or more ‘provider’ agencies. Many sources are also providers. Other
            agencies—e.g. the SDMX Global Registry—simply aggregate (meta)data from
            other providers, but do not provide any (meta)data themselves.
        resource : :class:`~.MaintainableArtefact` subclass
            Object to retrieve. If given, `resource_type` and `resource_id` are ignored.
        version : str
            :attr:`~.VersionableArtefact.version>` of a resource to retrieve. Default:
            the keyword 'latest'.

        Returns
        -------
        :class:`~.Message` or :class:`~requests.Request`
            The requested SDMX message or, if `dry_run` is :obj:`True`, the prepared
            request object.

        Raises
        ------
        NotImplementedError
            If the :attr:`source` does not support the given `resource_type` and `force`
            is not :obj:`True`.
        """
        # Insert resource_type and resource_id into kwargs
        kwargs.update(dict(resource_type=resource_type, resource_id=resource_id))

        kwargs = self._handle_get_kwargs(kwargs)

        # Handle arguments
        if "url" in kwargs:
            req = self._request_from_url(kwargs)
        else:
            req = self._request_from_args(kwargs)

        req = self.session.prepare_request(req)

        # Now get the SDMX message via HTTP
        log.info(f"Request {req.url}")
        log.info(f"with headers {req.headers}")

        # Try to get resource from memory cache if specified
        if use_cache:
            try:
                return self.cache[req.url]
            except KeyError:
                log.info("Not found in cache")
                pass

        if dry_run:
            return req

        try:
            # Send the request
            response = self.session.send(req, **self._send_kwargs)
            response.raise_for_status()
        except requests.exceptions.ConnectionError as e:
            raise e from None
        except requests.exceptions.HTTPError as e:
            # Convert a 501 response to a Python NotImplementedError
            if e.response.status_code == 501:
                raise NotImplementedError(
                    f"{resource_type!r} endpoint at {e.request.url}"
                )
            else:
                raise

        # Maybe copy the response to file as it's received
        response_content: "io.IOBase" = ResponseIO(response, tee=tofile)

        # Allow a source class to modify the response (e.g. headers) or content
        response, response_content = self.source.handle_response(
            response, response_content
        )

        # Select reader class
        content_type = response.headers.get("content-type", None)
        try:
            Reader = get_reader_for_media_type(content_type)
        except ValueError:
            raise ValueError(
                f"can't determine a reader for response content type {content_type!r}"
            ) from None

        # Instantiate reader
        reader = Reader()

        # Parse the message, using any provided or auto-queried DSD
        msg = reader.read_message(response_content, structure=kwargs.get("dsd", None))

        # Store the HTTP response with the message
        msg.response = response

        # Call the finish_message() hook
        msg = self.source.finish_message(msg, self, **kwargs)

        # store in memory cache if needed
        if use_cache:
            self.cache[req.url] = msg

        return msg

    def preview_data(self, flow_id, key={}):
        """Return a preview of data.

        For the Dataflow `flow_id`, return all series keys matching `key`. Uses a
        feature supported by some data providers that returns :class:`SeriesKeys
        <.SeriesKey>` without the corresponding
        :class:`Observations <.BaseObservation>`.

        To count the number of series::

            keys = sdmx.Client('PROVIDER').preview_data('flow')
            len(keys)

        To get a :mod:`pandas` object containing the key values::

            keys_df = sdmx.to_pandas(keys)

        Parameters
        ----------
        flow_id : str
            Dataflow to preview.
        key : dict, optional
            Mapping of `dimension` to `values`, where `values` may be a '+'-delimited
            list of values. If given, only SeriesKeys that match `key` are returned. If
            not given, preview_data is equivalent to
            ``list(client.series_keys(flow_id))``.

        Returns
        -------
        list of :class:`.SeriesKey`
        """
        # Retrieve the series keys
        all_keys = self.series_keys(flow_id)

        if len(key):
            # Construct a DSD from the keys
            dsd = DataStructureDefinition.from_keys(all_keys)

            # Make a ContentConstraint from *key*
            cc = dsd.make_constraint(key)

            # Filter the keys
            return [k for k in all_keys if k in cc]
        else:
            # No key is provided
            return list(all_keys)


def read_url(url, **kwargs):
    """Request a URL directly."""
    return Client().get(url=url, **kwargs)
