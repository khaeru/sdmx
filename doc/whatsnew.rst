:tocdepth: 2

What's new?
***********

.. contents::
   :local:
   :backlinks: none
   :depth: 1

Next release
============

Bug fixes
---------

- `attributes=` "d" ignored in :func:`.to_pandas` (:issue:`55`).

v2.0.0 (2021-01-26)
===================

Migration notes
---------------

Code that calls :func:`Request` emits :class:`DeprecationWarning` and logs a message with level :py:data:`~.logging.WARNING`:

.. code-block:: ipython

   >>> sdmx.Request("ECB")
   Request class will be removed in v3.0; use Client(...)
   <sdmx.client.Client object at 0x7f98787e7d60>

Instead, use:

.. code-block:: python

   sdmx.Client("ECB")

Per `the standard semantic versioning approach <https://semver.org/#how-should-i-handle-deprecating-functionality>`_, this feature is marked as deprecated in version 2.0, and will be removed no sooner than version 3.0.

References to ``sdmx.logger`` should be updated to ``sdmx.log``.
Instead of passing the `log_level` parameter to :class:`.Client`, access this standard Python :py:class:`~.logging.Logger` and change its level, as described at :ref:`HOWTO control logging <howto-logging>`.

All changes
-----------

- The large library of test specimens for :mod:`sdmx` is no longer shipped with the package, reducing the archive size by about 80% (:issue:`18`, :pull:`52`).
  The specimens can be retrieved for running tests locally; see :ref:`testing`.
- The :class:`Request` class is renamed :class:`.Client` for semantic clarity (:issue:`11`, :pull:`44`):

  A Client can open a :class:`.requests.Session` and might make many :class:`requests.Requests <.requests.Request>` against the same web service.

- The `log_level` parameter to :class:`.Client` is deprecated.
- Some internal modules are renamed.
  These should not affect user code; if they do, adjust that code to use the top-level objects.

  - :mod:`sdmx.api` is renamed :mod:`sdmx.client`.
  - :mod:`sdmx.remote` is renamed :mod:`sdmx.session`.
  - :mod:`sdmx.reader.sdmxml` is renamed :mod:`sdmx.reader.xml`, to conform with :mod:`sdmx.format.xml` and :mod:`sdmx.writer.xml`.
  - :mod:`sdmx.reader.sdmxjson` is renamed :mod:`sdmx.reader.json`.


v1.7.0 (2021-01-26)
===================

New features
------------

- Add :ref:`The Pacific Community's Pacific Data Hub <SPC>` as a data source (:pull:`30`).
- Add classes to :mod:`sdmx.model`: :class:`.TimeRangeValue`, :class:`.Period`, :class:`RangePeriod`, and parse ``<com:TimeRange>`` and related tags in SDMX-ML (:pull:`30`).

Bug fixes
---------

- Output SDMX-ML header elements in order expected by standard XSD (:issue:`42`, :pull:`43`).
- Respect `override` argument to :func:`.add_source` (:pull:`41`).

v1.6.0 (2020-12-16)
===================

New features
------------

- Support Python 3.9 (using pydantic ≥ 1.7) (:pull:`37`).
- Add :ref:`National Bank of Belgium <NBB>` as a data source (:pull:`32`).
- Add :ref:`Statistics Lithuania <LSD>` as a data source (:pull:`33`).

Bug fixes
---------

- Data set-level attributes were not collected by :class:`.sdmxml.Reader` (:issue:`29`, :pull:`33`).
- Respect `HTTP[S]_PROXY` environment variables (:issue:`26`, :pull:`27`).

v1.5.0 (2020-11-12)
===================

- Add a :doc:`brief tutorial <howto/create>` on creating SDMX-ML messages from pure Python objects (:issue:`23`, :pull:`24`).
- Add :ref:`Statistics Estonia <STAT_EE>` as a data source (:pull:`25`).
- Supply provider=“ALL” to :ref:`INSEE <INSEE>` structure queries by default (:issue:`21`, :pull:`22`)

v1.4.0 (2020-08-17)
===================

New features
------------

- Add :ref:`UNICEF <UNICEF>` service to supported sources (:pull:`15`).
- Enhance :func:`.to_xml` to handle :class:`DataMessages <.DataMessage>` (:pull:`13`).

  In v1.4.0, this feature supports a subset of DataMessages and DataSets.
  If you have an example of a DataMessages that :mod:`sdmx1` 1.4.0 cannot write, please `file an issue on GitHub <https://github.com/khaeru/sdmx/issues/new>`_ with a file attachment.
  SDMX-ML features used in such examples will be prioritized for future improvements.

- Add ``compare()`` methods to :class:`.DataMessage`, :class:`.DataSet`, and related classes  (:pull:`13`).

Bug fixes
---------

- Fix parsing of :class:`.MeasureDimension` returned by :ref:`SGR <SGR>` for data structure queries (:pull:`14`).

v1.3.0 (2020-08-02)
===================

- Adjust imports for compatibility with pandas 1.1.0 (:pull:`10`).
- Add :ref:`World Bank World Development Indicators (WDI) <WB_WDI>` service to supported sources (:pull:`10`).


v1.2.0 (2020-06-04)
===================

New features
------------

- Methods like :meth:`.IdentifiableArtefact.compare` are added for recursive comparison of :mod:`.model` objects (:pull:`6`).
- :func:`.to_xml` covers a larger subset of SDMX-ML, including almost all contents of a :class:`.StructureMessage` (:pull:`6`).


v1.1.0 (2020-05-18)
===================

Data model changes
------------------

…to bring :mod:`sdmx` into closer alignment with the standard Information Model (:pull:`4`):

- Change :attr:`.Header.receiver` and :attr:`.Header.sender` to optional :class:`.Agency`, not :class:`str`.
- Add :attr:`.Header.source` and :attr:`~.Header.test`.
- :attr:`.IdentifiableArtefact.id` is strictly typed as :class:`str`, with a singleton object (analogous to :obj:`None`) used for missing IDs.
- :attr:`.IdentifiableArtefact.id`, :attr:`.VersionableArtefact.version`, and :attr:`.MaintainableArtefact.maintainer` are inferred from a URN if one is passed during construction.
- :meth:`.VersionableArtefact.identical` and :meth:`.MaintainableArtefact.identical` compare on version and maintainer attributes, respectively.
- :class:`.Facet`, :class:`.Representation`, and :class:`.ISOConceptReference` are strictly validated, i.e. cannot be assigned non-IM attributes.
- Add :class:`.OrganisationScheme`, :class:`.NoSpecifiedRelationship`, :class:`.PrimaryMeasureRelationship`, :class:`.DimensionRelationship`, and :class:`.GroupRelationship` as distinct classes.
- Type of :attr:`.DimensionRelationship.dimensions` is :class:`.DimensionComponent`, not the narrower :class:`.Dimension`.
- :attr:`.DataStructureDefinition.measures` is an empty :class:`.MeasureDescriptor` by default, not :obj:`None`.
- :meth:`.DataSet.add_obs` now accepts :class:`Observations <.Observation>` with no :class:`.SeriesKey` association, and sets this association to the one provided as an argument.
- String representations are simplified but contain more information.

New features
------------

- :attr:`.Item.hierarchical_id` and :meth:`.ItemScheme.get_hierarchical` create and search on IDs like ‘A.B.C’ for Item ‘A’ with child/grandchild Items ‘B’ and ‘C’ (:pull:`4`).
- New methods :func:`.parent_class`, :func:`.get_reader_for_path`, :func:`.detect_content_reader`, and :func:`.reader.register` (:pull:`4`).
- :class:`.sdmxml.Reader` uses an event-driven, rather than recursive/tree iterating, parser (:pull:`4`).
- The codebase is improved to pass static type checking with `mypy <https://mypy.readthedocs.io>`_ (:pull:`4`).
- Add :func:`.to_xml` to generate SDMX-ML for a subset of the IM (:pull:`3`).

Test suite
----------

- :pull:`2`: Add tests of data queries for source(s): OECD


v1.0.0 (2020-05-01)
===================

- Project forked and renamed to :mod:`sdmx` (module) / ``sdmx1`` (on PyPI, due to an older, unmaintained package with the same name).
- :mod:`sdmx.model` is reimplemented.

  - Python typing_ and pydantic_ are used to force tight compliance with the SDMX Information Model (IM).
    Users familiar with the IM can use :mod:`sdmx` without the need to understand implementation-specific details.
  - IM classes are no longer tied to :mod:`sdmx.reader` instances and can be created and manipulated outside of a read operation.

- :mod:`sdmx.api` and :mod:`sdmx.remote` are reimplemented to (1) match the semantics of the requests_ package and (2) be much thinner.
- Data sources are modularized in :class:`~.source.Source`.

  - Idiosyncrasies of particular data sources (e.g. ESTAT's process for large requests) are handled by source-specific subclasses.
    As a result, :mod:`sdmx.api` is leaner.

- Testing coverage is significantly expanded.

  - Promised, but untested, features of the 0.x series now have tests, to ensure feature parity.
  - There are tests for each data source (:file:`tests/test_sources.py``) to ensure the package can handle idiosyncratic behaviour.
  - The pytest-remotedata_ pytest plugin allows developers and users to run or skip network tests with `--remote-data`.

.. _typing: https://docs.python.org/3/library/typing.html
.. _pydantic: https://pydantic-docs.helpmanual.io
.. _requests: http://docs.python-requests.org
.. _pytest-remotedata: https://github.com/astropy/pytest-remotedata

Breaking changes
----------------
- Python 3.6 and earlier (including Python 2) are not supported.

Migrating
---------
- ``Writer.write(…, reverse_obs=True)``: use the standard pandas indexing approach to reverse a pd.Series: ``s.iloc[::-1]``
- odo support is no longer built-in; however, users can still register a SDMX resource with odo.
  See the :ref:`HOWTO <howto-convert>`.
- :func:`.write_dataset`: the `parse_time` and `fromfreq` arguments are replaced by `datetime`; see the method documentation and the :ref:`walkthrough section <datetime>` for examples.


pandaSDMX (versions 0.9 and earlier)
====================================

pandaSDMX v0.9 (2018-04)
------------------------

This version is the last tested on Python 2.x.
Future versions will be tested on Python 3.5+ only

New features
::::::::::::

* four new data providers INEGI (Mexico), Norges Bank (Norway), International Labour Organization (ILO) and Italian statistics office (ISTAT)
* model: make Ref instances callable for resolving them, i.e. getting the referenced object by making a remote request if needed
* improve loading of structure-specific messages when DSD is not passed / must be requested on the fly
* process multiple and cascading content constraints as described in the Technical Guide (Chap. 6 of the SDMX 2.1 standard)
* StructureMessages and DataMessages now have properties to compute the constrained and unconstrained codelists as dicts of frozensets of codes.
  For DataMessage this is useful when ``series_keys`` was set to True when making the request.
  This prompts the data provider to generate a dataset without data, but with the complete set of series keys.
  This is the most accurate representation of the available series.
  Agencies such as IMF and ECB support this feature.

v0.8.2 (2017-12-21)
-------------------

* fix reading of structure-specific data sets when DSD_ID is present in the data set

v0.8.1 (2017-12-20)
-------------------

* fix broken  package preventing pip installs of the wheel


v0.8 (2017-12-12)
-----------------

* add support for an alternative data set format defined for SDMXML messages.
  These so-called structure-specific data sets lend themselves for large data queries.
  File sizes are typically about 60 % smaller than with equivalent generic data sets.
  To make use of structure-specific data sets, instantiate Request objects with agency IDs such as 'ECB_S', 'INSEE_S' or 'ESTAT_S' instead of 'ECB' etc.
  These alternative agency profiles prompt pandaSDMX to execute data queries for structure-specific data sets.
  For all other queries they behave exactly as their siblings.
  See a code example in chapter 5 of the docs.
* raise ValueError when user attempts to request a resource other than data from an agency delivering data in SCMX-JSON format only (OECD and ABS).
* Update INSEE profile
* handle empty series properly
* data2pd writer: the code for Series index generation was rewritten from scratch to make better use of pandas' time series functionality.
  However, some data sets, in particular from INSEE, which come with bimonthly or semestrial frequencies cannot be rendered as PeriodIndex.
  Pass ``parse_time=False`` to the .write method to prevent errors.


v0.7.0 (2017-06-10)
-------------------

* add new data providers:

  - Australian Bureau of Statistics
  - International Monetary Fund - SDMXCentral only
  - United Nations Division of Statistics
  - UNESCO (free registration required)
  - World Bank - World Integrated Trade Solution (WITS)

* new feature: load metadata on data providers from json file; allow the user to add new agencies on the fly by specifying an appropriate JSON file using the :meth:`pandasdmx.api.Request.load_agency_profile`.
* new :meth:`pandasdmx.api.Request.preview_data` providing a powerful fine-grain key validation algorithm by downloading all series-keys of a dataset and exposing them as a pandas DataFrame which is then mapped to the cartesian product of the given dimension values.
  Works only with data providers such as ECB and UNSD which support "series-keys-only" requests.
  This feature could be wrapped by a browser-based UI for building queries.
* sdjxjson reader: add support for flat and cross-sectional datasets, preserve dimension order where possible
* structure2pd writer: in codelists, output Concept rather than Code attributes in the first line of each code-list.
  This may provide more information.

v0.6.1 (2017-02-03)
-------------------

* fix 2to3 issue which caused crashes on Python 2.7


v0.6 (2017-01-07)
-----------------

This release contains some important stability improvements.

Bug fixes
:::::::::

* JSON data from OECD is now properly downloaded
* The data writer tries to gleen a frequency value for a time series from its attributes.
  This is helpful when exporting data sets, e.g., from INSEE (`Issue 41 <https://github.com/dr-leo/pandaSDMX/issues/41>`_).

Known issues
::::::::::::

A data set which lacks a FREQ dimension or attribute can be exported as pandas DataFrame only when `parse_time=False?`, i.e. no DateTime index is generated.
The resulting DataFrame has a string index.
Use pandas magic to create a DateTimeIndex from there.

v0.5 (2016-10-30)
-----------------

New features
::::::::::::

* new reader module for SDMX JSON data messages
* add OECD as data provider (data messages only)
* :class:`pandasdmx.model.Category` is now an iterator over categorised objects.
  This greatly simplifies category usage.
  Besides, categories with the same ID while belonging to multiple category schemes are no longer conflated.


API changes
:::::::::::

* Request constructor: make agency ID case-insensitive
* As :class:`Category` is now an iterator over categorised objects, :class:`Categorisations` is no longer considered part of the public API.

Bug fixes
:::::::::

* sdmxml reader: fix AttributeError in write_source method, thanks to Topas
* correctly distinguish between categories with same ID while belonging to different category schemes


v0.4 (2016-04-11)
-----------------

New features
::::::::::::

* add new provider INSEE, the French statistics office (thanks to Stéphan Rault)
* register '.sdmx' files with `Odo <odo.readthedocs.io/>`_ if available
* logging of http requests and file operations.
* new structure2pd writer to export codelists, dataflow-definitions and other structural metadata from structure messages as multi-indexed pandas DataFrames.
  Desired attributes can be specified and are represented by columns.

API changes
:::::::::::

* :class:`pandasdmx.api.Request` constructor accepts a ``log_level`` keyword argument which can be set to a log-level for the pandasdmx logger and its children (currently only pandasdmx.api)
* :class:`pandasdmx.api.Request` now has a ``timeout`` property to set the timeout for http requests
* extend api.Request._agencies configuration to specify agency- and resource-specific settings such as headers.
  Future versions may exploit this to provide reader selection information.
* api.Request.get: specify http_headers per request. Defaults are set according to agency configuration
* Response instances expose Message attributes to make application code more succinct
* rename :class:`pandasdmx.api.Message` attributes to singular form.
  Old names are deprecated and will be removed in the future.
* :class:`pandasdmx.api.Request` exposes resource names such as data, datastructure, dataflow etc. as descriptors calling 'get' without specifying the resource type as string.
  In interactive environments, this saves typing and enables code completion.
* data2pd writer: return attributes as namedtuples rather than dict
* use patched version of namedtuple that accepts non-identifier strings as field names and makes all fields accessible through dict syntax.
* remove GenericDataSet and GenericDataMessage. Use DataSet and DataMessage instead
* sdmxml reader: return strings or unicode strings instead of LXML smart strings
* sdmxml reader: remove most of the specialized read methods.
  Adapt model to use generalized methods. This makes code more maintainable.
* :class:`pandasdmx.model.Representation` for DSD attributes and dimensions now supports text not just codelists.

Other changes and enhancements
::::::::::::::::::::::::::::::

* documentation has been overhauled.
  Code examples are now much simpler thanks to the new structure2pd writer
* testing: switch from nose to py.test
* improve packaging. Include tests in sdist only
* numerous bug fixes

v0.3.1 (2015-10-04)
-------------------

This release fixes a few bugs which caused crashes in some situations.

v0.3.0 (2015-09-22)
-------------------

* support for `requests-cache <https://readthedocs.io/projects/requests-cache/>`_ allowing to cache SDMX messages in memory, MongoDB, Redis or SQLite.
* pythonic selection of series when requesting a dataset: Request.get allows the ``key`` keyword argument in a data request to be a dict mapping dimension names to values.
  In this case, the dataflow definition and datastructure definition, and content-constraint are downloaded on the fly, cached in memory and used to validate the keys.
  The dotted key string needed to construct the URL will be generated automatically.
* The Response.write method takes a ``parse_time`` keyword arg. Set it to False to avoid parsing of dates, times and time periods as exotic formats may cause crashes.
* The Request.get method takes a ``memcache`` keyward argument.
  If set to a string, the received Response instance will be stored in the dict ``Request.cache`` for later use.
  This is useful when, e.g., a DSD is needed multiple times to validate keys.
* fixed base URL for Eurostat
* major refactorings to enhance code maintainability

v0.2.2
------

* Make HTTP connections configurable by exposing the `requests.get API <http://www.python-requests.org/en/latest/>`_ through the :class:`pandasdmx.api.Request` constructor.
  Hence, proxy servers, authorisation information and other HTTP-related parameters consumed by ``requests.get`` can be specified for each ``Request`` instance and used in subsequent requests.
  The configuration is exposed as a dict through a new ``Request.client.config`` attribute.
* Responses have a new ``http_headers`` attribute containing the HTTP headers returned by the SDMX server

v0.2.1
------

* Request.get: allow `fromfile` to be a file-like object
* extract SDMX messages from zip archives if given.
  Important for large datasets from Eurostat
* automatically get a resource at an URL given in the footer of the received message.
  This allows to automatically get large datasets from Eurostat that have been made available at the given URL.
  The number of attempts and the time to wait before each request are configurable via the ``get_footer_url`` argument.


v0.2.0 (2015-04-13)
-------------------

This version is a quantum leap.
The whole project has been redesigned and rewritten from scratch to provide robust support for many SDMX features.
The new architecture is centered around a pythonic representation of the SDMX information model.
It is extensible through readers and writers for alternative input and output formats.
Export to pandas has been dramatically improved.
Sphinx documentation has been added.

v0.1.2 (2014-09-17)
-------------------

* fix xml encoding. This brings dramatic speedups when downloading and parsing data
* extend description.rst


v0.1 (2014-09)
--------------

* Initial release
