.. currentmodule:: sdmx

Data sources
============

SDMX makes a distinction between data providers and sources:

- a **data provider** is the original publisher of statistical information and metadata.
- a **data source** is a specific web service that provides access to statistical information.

Each data *source* might aggregate and provide data or metadata from multiple data *providers*.
Or, an agency might operate a data source that only contains information they provide themselves; in this case, the source and provider are identical.

:mod:`sdmx` identifies each data source using a string such as ``'ABS'``, and has built-in support for a number of data sources.
Use :meth:`list_sources` to list these.
Read the following sections, or the file :file:`sources.json` in the package source code, for more details.

:mod:`sdmx` also supports adding other data sources; see :meth:`add_source` and :class:`~.source.Source`.

Data source limitations
-----------------------

Each SDMX web service provides a subset of the full SDMX feature set, so the same request made to two different sources may yield different results, or an error message.
In order to anticipate and handle these differences:

1. :meth:`add_source` accepts "data_content_type" and "supported" keys. For
   example:

   .. code-block:: json

      [
        {
          "id": "ABS",
          "data_content_type": "JSON"
        },
        {
          "id": "UNESCO",
          "supported": {"datastructure": false}
        },
      ]

   :mod:`sdmx` will raise :class:`NotImplementedError` on an attempt to query the "datastructure" API endpoint of either of these data sources.

2. :mod:`sdmx.source` includes adapters (subclasses of :class:`~.source.Source`) with hooks used when querying sources and interpreting their HTTP responses.
   These are documented below, e.g. ABS_, ESTAT_, and SGR_.

.. _source-policy:

Handling and testing limitations and (un)supported endpoints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As of version 2.5.0, :mod:`sdmx` handles service limitations as follows.
Please `open an issue <https://github.com/khaeru/sdmx/issues/new>`__ if the supported endpoints or behaviour of a particular service appear to have changed.

- :attr:`.source.Source.supports` lists endpoints/:class:`resources <.Resource>` that are not supported by *any* known web service.
- :file:`sources.json` contains ``supports: {"[resource]": false}`` for any endpoint where the service returns an HTTP **404 Not found** response code.
  This means that the service fails to even give a proper 501 response (see below).

  :meth:`.Client.get` will refuse to query these sources at all, instead raising :class:`NotImplementedError`.
  You can override this behaviour by giving the `force` argument to :meth:`~.Client.get`.

- The test suite (:mod:`test_sources`) includes notation of all endpoints for which services return **400 Bad syntax** or **501 Not implemented** response codes.
  :mod:`sdmx` will make an actual query to these endpoints, but raise built-in Python exceptions that can be caught and handled by user code:

  - For a 501 response code, :class:`NotImplementedError` is raised.

    This is behaviour *fully compliant with the SDMX standard*: the service accurately and honestly responds when a client makes a request that the server does not implement.

  - For a 400 response code, :class:`HTTPError` is raised.

    Some of these “bad syntax” responses are erroneous: the service actually has a *non-standard* URL scheme or handling, different from the SDMX-REST standard.
    The :class:`.Client` is constructing a standards-compliant URL, but the service idiosyncratically rejects it.
    Handling these idiosyncrasies is currently out-of-scope for :mod:`sdmx`.

.. _source-matrix:

- Because of the large number of services and endpoints, the matrix of support is only periodically updated.
  To mitigate: https://khaeru.github.io/sdmx/ displays a summary of every SDMX 2.1 REST API endpoint for every data source built-in to :mod:`sdmx`; this summary is updated daily by an automatic run of the test suite.
  These include all endpoints known to return a non-404 reply, even if the reply is an error message of some sort.


SDMX-JSON versus SDMX-ML services
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A key difference is between sources offering SDMX-ML and SDMX-JSON content.
Although the SDMX-JSON format includes structure messages, initial/draft versions of it, and so many web services that return SDMX-JSON still do not support structure queries; only data queries.
As well, the SDMX-REST standard allows services to respond to the HTTP ``Accepts:`` header and return either SDMX-ML or SDMX-JSON, only a few services actually implement this feature.

Where data structures are not available, :mod:`sdmx` cannot automatically validate keys.
For such services, start by browsing the source's website to identify a dataflow of interest.
Then identify the key format and construct a key for the desired data request.


.. _ABS:

``ABS``: Australian Bureau of Statistics (SDMX-ML)
--------------------------------------------------

SDMX-ML —
`Website <https://www.abs.gov.au/about/data-services/application-programming-interfaces-apis/data-api-user-guide>`__

.. versionadded:: 2.10.0


.. _ABS_JSON:

``ABS_JSON``: Australian Bureau of Statistics (SDMX-JSON)
---------------------------------------------------------

SDMX-JSON —
`Website <https://www.abs.gov.au/about/data-services/application-programming-interfaces-apis/data-api-user-guide>`__

.. autoclass:: sdmx.source.abs_json.Source()
   :members:


.. _BBK:

``BBK``: German Federal Bank
----------------------------

SDMX-ML —
Website `(en) <https://www.bundesbank.de/en/statistics/time-series-databases/-/help-for-sdmx-web-service-855900>`__,
`(de) <https://www.bundesbank.de/de/statistiken/zeitreihen-datenbanken/hilfe-zu-sdmx-webservice>`__

.. versionadded:: 2.5.0

- German name: Deutsche Bundesbank
- The web service has some non-standard behaviour; see :issue:`82`.
- The `version` path component is not-supported for non-data endpoints.
  :mod:`sdmx` discards other values with a warning.
- Some endpoints, including :data:`.codelist`, return malformed URNs and cannot be handled with :mod:`sdmx`.

.. autoclass:: sdmx.source.bbk.Source()
   :members:


.. _BIS:

``BIS``: Bank for International Settlements
-------------------------------------------

SDMX-ML —
`Website <https://www.bis.org/statistics/sdmx_techspec.htm>`__ —
`API reference <https://stats.bis.org/api-doc/v1/>`__

.. versionadded:: 2.5.0


.. _ECB:

``ECB``: European Central Bank
------------------------------

SDMX-ML —
`Website <https://www.ecb.europa.eu/stats/ecb_statistics/co-operation_and_standards/sdmx/html/index.en.html>`__

- Supports categorisations of data-flows.
- Supports preview_data and series-key based key validation.
- In general short response times.


.. _ESTAT:

``ESTAT``: Eurostat and related
-------------------------------

SDMX-ML —
Website `1 <https://wikis.ec.europa.eu/pages/viewpage.action?pageId=40708145>`__,
`2 <https://wikis.ec.europa.eu/pages/viewpage.action?pageId=44165555>`__

- Eurostat also maintains four additional SDMX REST API endpoints, available in :mod:`sdmx` with the IDs below.
  These are described at URL (2) above.

.. contents::
    :local:

- In some cases, the service can have a long response time, so :mod:`sdmx` will time out.
  Increase the timeout attribute if necessary.

.. autoclass:: sdmx.source.estat.Source()
   :members:

.. _ESTAT_COMEXT:

``ESTAT_COMEXT``: Eurostat Comext and Prodcom databases
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- The :class:`.Agency` ID for data is still ``ESTAT``.

.. _COMP:
.. _EMPL:
.. _GROW:

``COMP``, ``EMPL``, ``GROW``: Directorates General of the European Commission
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These are, respectively:

- ``COMP``: Directorate General for Competition.
- ``EMPL``: Directorate General for Employment, Social Affairs and inclusion.
- ``GROW``: Directorate General for Internal Market, Industry, Entrepreneurship and SMEs.

No separate online documentation appears to exist for these API endpoints.
In order to identify available data flows:

.. code-block:: python

   COMP = sdmx.Client("COMP")
   sm = COMP.dataflow()
   print(sm.dataflow)


.. _ILO:

``ILO``: International Labour Organization
------------------------------------------

SDMX-ML —
`Website <https://ilostat.ilo.org/resources/sdmx-tools/>`__

- :class:`sdmx.source.ilo.Source` handles some particularities of the ILO web service, including:

  - The ``references=`` query parameter is not supported; any value is discarded with a warning.

  Others that are not handled:

  - Data flow IDs take on the role of a filter.
    E.g., there are dataflows for individual countries, ages, sexes etc. rather than merely for different indicators.
  - The service returns 413 Payload Too Large errors for some queries, with messages like: "Too many results, please specify codelist ID".
    Test for :class:`sdmx.exceptions.HTTPError` (= :class:`requests.exceptions.HTTPError`) and/or specify a ``resource_id``.

- It is highly recommended to read the “ILOSTAT SDMX User Guide” linked from the above webpage.

.. autoclass:: sdmx.source.ilo.Source()
   :members:


.. _IMF:

``IMF``: International Monetary Fund's “SDMX Central” source
------------------------------------------------------------

SDMX-ML —
`Website <https://sdmxcentral.imf.org/>`__

- Subset of the data available on http://data.imf.org.
- Supports series-key-only and hence dataset-based key validation and construction.


.. _INEGI:

``INEGI``: National Institute of Statistics and Geography (Mexico)
------------------------------------------------------------------

SDMX-ML —
`Website <https://sdmx.snieg.mx/infrastructure>`__.

- Spanish name: Instituto Nacional de Estadística y Geografía.


.. _INSEE:

``INSEE``: National Institute of Statistics and Economic Studies (France)
-------------------------------------------------------------------------

SDMX-ML —
Website `(en) <https://www.insee.fr/en/information/2868055>`__,
`(fr) <https://www.insee.fr/fr/information/2862759>`__

- French name: Institut national de la statistique et des études économiques.

.. autoclass:: sdmx.source.insee.Source()
   :members:


.. _ISTAT:

``ISTAT``: National Institute of Statistics (Italy)
---------------------------------------------------

SDMX-ML —
Website `(en) <https://www.istat.it/en/methods-and-tools/sdmx-web-service>`__,
`(it) <https://www.istat.it/it/metodi-e-strumenti/web-service-sdmx>`__

- Italian name: Istituto Nazionale di Statistica.
- Similar server platform to Eurostat, with similar capabilities.
- Distinct API endpoints are available for:

  - 2010 Agricultural census
  - 2011 Population and housing census
  - 2011 Industry and services census

  …see the above URLs for details.


.. _LSD:

``LSD``: National Institute of Statistics (Lithuania)
-----------------------------------------------------

SDMX-ML —
`Website <https://osp.stat.gov.lt/rdb-rest>`__

- Lithuanian name: Lietuvos statistikos.
- This web service returns the non-standard HTTP content-type "application/force-download"; :mod:`sdmx` replaces it with "application/xml".


.. _NB:

``NB``: Norges Bank (Norway)
----------------------------

SDMX-ML —
`Website <https://www.norges-bank.no/en/topics/Statistics/open-data/>`__

- Few dataflows. So do not use categoryscheme.
- It is unknown whether NB supports series-keys-only.


.. _NBB:

``NBB``: National Bank of Belgium (Belgium)
-------------------------------------------

SDMX-JSON —
`Website <https://stat.nbb.be/>`__ —
API documentation `(en) <https://www.nbb.be/doc/dq/migratie_belgostat/en/nbb_stat-technical-manual.pdf>`__

- French name: Banque Nationale de Belgique.
- Dutch name: Nationale Bank van België.
- As of 2020-12-13, this web service (like STAT_EE) uses server software that serves SDMX-ML 2.0 or SDMX-JSON.
  Since :mod:`sdmx` does not support SDMX-ML 2.0, the package is configured to use the JSON endpoint.
- The web service returns a custom HTML error page rather than an SDMX error message for certain queries or an internal error.
  This appears as: ``ValueError: can't determine a SDMX reader for response content type 'text/html; charset=utf-8'``


.. _OECD:

``OECD``: Organisation for Economic Cooperation and Development
---------------------------------------------------------------

SDMX-JSON —
`Website <https://data.oecd.org/api/sdmx-json-documentation/>`__

The OECD website `describes an SDMX-ML API <https://data.oecd.org/api/sdmx-ml-documentation/>`__, but this is an implementation of SDMX 2.0, which is not supported by :mod:`sdmx` (see :ref:`sdmx-version-policy`).


.. _SGR:

``SGR``: SDMX Global Registry
-----------------------------

SDMX-ML —
`Website <https://registry.sdmx.org/overview.html>`__

.. autoclass:: sdmx.source.sgr.Source()
   :members:


.. _SPC:

``SPC``: Pacific Data Hub DotStat by the Pacific Community (SPC)
----------------------------------------------------------------

SDMX-ML —
`API documentation <https://docs.pacificdata.org/dotstat/>`__ —
`Web interface <https://stats.pacificdata.org/>`__

- French name: Communauté du Pacifique


.. _STAT_EE:

``STAT_EE``: Statistics Estonia (Estonia)
-----------------------------------------

SDMX-JSON —
`Website <https://andmebaas.stat.ee>`__ (et) —
API documentation `(en) <https://www.stat.ee/sites/default/files/2020-09/API-instructions.pdf>`__,
`(et) <https://www.stat.ee/sites/default/files/2020-09/API-juhend.pdf>`__

- Estonian name: Eesti Statistika.
- As of 2023-05-19, the site displays a message:

    From March 2023 onwards, data in this database are no longer updated!
    Official statistics can be found in the database at `andmed.stat.ee <https://andmed.stat.ee>`__.

  The latter URL indicates an API is provided, but it is not an SDMX API, and thus not supported.
- As of 2020-12-13, this web service (like NBB) uses server software that serves SDMX-JSON or SDMX-ML 2.0.
  The latter is not supported by :mod:`sdmx` (see :ref:`sdmx-version-policy`).


.. _UNESCO:

``UNESCO``: UN Educational, Scientific and Cultural Organization
----------------------------------------------------------------

SDMX-ML —
`Website <https://apiportal.uis.unesco.org/getting-started>`__

- Free registration required; user credentials must be provided either as parameter or HTTP header with each request.

.. warning:: An issue with structure-specific datasets has been reported.
   It seems that Series are not recognized due to some oddity in the XML format.


.. _UNICEF:

``UNICEF``: UN Children's Fund
------------------------------

SDMX-ML or SDMX-JSON —
`API documentation <https://data.unicef.org/sdmx-api-documentation/>`__ —
`Web interface <https://sdmx.data.unicef.org/>`__ —
`Data browser <https://sdmx.data.unicef.org/databrowser/index.html>`__

- This source always returns structure-specific messages for SDMX-ML data queries; even when the HTTP header ``Accept: application/vnd.sdmx.genericdata+xml`` is given.

.. _CD2030:

- UNICEF also serves data for the `Countdown to 2030 <https://www.countdown2030.org/about>`_ initiative under a data flow with the ID ``CONSOLIDATED``.
  The structures can be obtained by giving the `provider` argument to a structure query, and then used to query the data:

  .. code-block:: python

     import sdmx

     UNICEF = sdmx.Client("UNICEF")

     # Use the dataflow ID to obtain the data structure definition
     dsd = UNICEF.dataflow("CONSOLIDATED", provider="CD2030").structure[0]

     # Use the DSD to construct a query for indicator D5 (“Births”)
     client.data("CONSOLIDATED", key=dict(INDICATOR="D5"), dsd=dsd)

- The example query from the UNICEF API documentation (also used in the :mod:`sdmx` test suite) returns XML like:

  .. code-block:: xml

     <mes:Structure structureID="UNICEF_GLOBAL_DATAFLOW_1_0" namespace="urn:sdmx:org.sdmx.infomodel.datastructure.Dataflow=UNICEF:GLOBAL_DATAFLOW(1.0):ObsLevelDim:TIME_PERIOD" dimensionAtObservation="TIME_PERIOD">
       <com:StructureUsage>
         <Ref agencyID="UNICEF" id="GLOBAL_DATAFLOW" version="1.0"/>
       </com:StructureUsage>
     </mes:Structure>

  Contrary to this, the corresponding DSD actually has the ID ``DSD_AGGREGATE``, not ``GLOBAL_DATAFLOW``.
  To retrieve the DSD—which is necessary to parse a data message—first query this data *flow* by ID, and select the DSD from the returned message:

  .. ipython:: python

     import sdmx
     msg = sdmx.Client("UNICEF").dataflow("GLOBAL_DATAFLOW")
     msg
     dsd = msg.structure[0]

  The resulting object `dsd` can be passed as an argument to a :meth:`.Client.get` data query.
  See the `sdmx test suite <https://github.com/khaeru/sdmx/blob/main/sdmx/tests/test_sources.py>`_ for an example.


.. _UNSD:

``UNSD``: United Nations Statistics Division
--------------------------------------------

SDMX-ML —
`Website <https://unstats.un.org/home/>`__

- Supports preview_data and series-key based key validation.


.. _WB:

``WB``: World Bank Group “World Integrated Trade Solution”
----------------------------------------------------------

SDMX-ML —
`Website <https://wits.worldbank.org>`__


.. _WB_WDI:

``WB_WDI``: World Bank Group “World Development Indicators”
-----------------------------------------------------------

SDMX-ML —
`Website <https://datahelpdesk.worldbank.org/knowledgebase/articles/1886701-sdmx-api-queries>`__

- This web service also supports SDMX-JSON.
  To retrieve messages in this format, pass the HTTP ``Accept:`` header described on the service website.


Source API
----------

.. currentmodule:: sdmx.source

This module defines :class:`Source <sdmx.source.Source>` and some utility functions.
For built-in subclasses of Source used to provide :mod:`sdmx`'s built-in support for certain data sources, see :doc:`sources`.

.. autoclass:: sdmx.source.Source()
   :members:

   This class should not be instantiated directly.
   Instead, use :func:`.add_source`, and then create a new :class:`.Client` with the corresponding source ID.

.. automodule:: sdmx.source
   :members: list_sources, load_package_sources
