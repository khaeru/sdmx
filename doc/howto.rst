How to…
=======

On other pages:

.. toctree::
   :maxdepth: 1

   howto/create
   howto/validate

Access other SDMX data sources
------------------------------

:mod:`sdmx` ships with a file, `sources.json`, that includes information about the capabilities of many :doc:`data sources <sources>`.
However, any data source that generates SDMX 2.1 messages is supported.
There are multiple ways to access these:

1. Create a :class:`sdmx.Client` without a named data source, then call the :meth:`~.Client.get` method using the `url` argument::

    import sdmx
    c = sdmx.Client()
    c.get(url='https://sdmx.example.org/path/to/webservice', ...)

2. Call :meth:`~sdmx.source.add_source` with a JSON snippet describing the data provider.

3. Create a subclass of :class:`~sdmx.source.Source`, providing attribute values and optional implementations of hooks.


.. _howto-logging:

Control logging
---------------

:obj:`sdmx.log` is a standard Python :class:`logging.Logger` object.
For debugging, set this to a permissive level:

.. code-block:: python

   import logging

   sdmx.log.setLevel(logging.DEBUG)

Log messages include the web service query details (URL and headers) used by :class:`.Client`.


.. _howto-references:

Use the 'references' query parameter
------------------------------------

SDMX web services support a ``references`` parameter in HTTP requests which can take values such as 'all', 'descendants', etc.
This parameter instructs the web service to include, when generating a Data- or StructureMessage, the objects implicitly designated by the ``references`` parameter alongside the explicit resource.
For example, for the request:

>>> response = some_agency.dataflow('SOME_ID', params={'references': 'all'})

the response will include:

- the dataflow 'SOME_ID' explicitly specified,
- the DSD referenced by the dataflow's ``structure`` attribute,
- the code lists referenced by the DSD, and
- any content-constraints which reference the dataflow or the DSD.

It is much more efficient to request many objects in a single request.
Thus, :mod:`sdmx` provides default values for ``references`` in common queries.
For instance, when a single dataflow is requested by specifying its ID, :mod:`sdmx` sets ``references`` to 'all'.
On the other hand, when the dataflow ID is wild-carded, it is more practical not to request all referenced objects alongside as the response would likely be excessively large, and the user is deemed to be interested in the bird's eye perspective (list of data flows) prior to focusing on a particular dataflow and its descendants and ancestors.
The default value for the ``references`` parameter can be overridden.

Some web services differ in how they handle ``references``—for instance, :ref:`ESTAT <ESTAT>`.
See :doc:`sources` for details.


.. _howto-categoryscheme:

Use category schemes to explore data
------------------------------------

SDMX supports category-schemes to categorize dataflow definitions and other objects.
This helps retrieve, e.g., a dataflow of interest. Note that not all agencies support category schemes.
A good example is the ECB.
However, as the ECB's SDMX service offers less than 100 data flows, using category schemes is not strictly necessary.
A counter-example is Eurostat which offers more than 6000 data flows, yet does not categorize them.
Hence, the user must search through the flat list of data flows.

To search the list of data flows by category, we request the category scheme from the ECB's SDMX service and explore the response:

.. ipython:: python

    import sdmx
    ecb = sdmx.Client('ecb')
    cat_response = ecb.categoryscheme()

Like any other scheme, a category scheme is essentially a dict mapping ID's to the actual SDMX objects.
To display the categorized items, in our case the dataflow definitions contained in the category on exchange rates, we iterate over the `Category` instance:

.. ipython:: python

    sdmx.to_pandas(cat_response.category_scheme.MOBILE_NAVI)
    cat_response.category_scheme.MOBILE_NAVI

.. versionadded:: 0.5


.. _howto-rtype:

Select data frame layouts returned by :func:`.to_pandas`
--------------------------------------------------------

:func:`.to_pandas` provides multiple ways to customize the type and layout of pandas objects returned for :class:`.DataMessage` input.
One is the `datetime` argument; see :ref:`datetime`.
The other is the `rtype` argument.

To select the same behaviour as pandaSDMX 0.9, give `rtype` = 'compat', or set :data:`.DEFAULT_RTYPE` to 'compat':

.. ipython:: python

   sdmx.writer.DEFAULT_RYPE = 'compat'

With 'compat', the returned layout varies with the concept of “dimension at the observation level,” as follows:

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Dimension At Observation Level
     - Return Type
   * - :data:`.AllDimensions`
     - - :class:`~pandas.Series`, without attributes, or
       - :class:`~pandas.DataFrame`, with any attributes.
   * - :class:`.TimeDimension`
     - Same as `datetime` = :obj:`True` —a :class:`~pandas.Dataframe` with:

       - index: :class:`~pandas.DatetimeIndex` or :class:`~pandas.PeriodIndex`, and
       - columns: :class:`~pandas.MultiIndex` with all other dimensions.
   * - Other :class:`.Dimension`
     - :class:`~pandas.DataFrame` with:

       - index: the dimension at observation level, and
       - columns: :class:`~pandas.MultiIndex` with all other dimensions.

Limitations:

- :mod:`sdmx` can only obey `rtype` = 'compat' when reading or converting an entire :class:`.DataMessage`; not a :class:`.DataSet`.
  While the concept of “dimension at observation level” is *mentioned* in the IM in relation to data sets, it is not formally included as an attribute of any class, or with any default value.
  (For instance, it is not included in the :class:`.DimensionDescriptor` of a :class:`DataStructureDefinition <.BaseDataStructureDefinition>`.)
  It can *only* be determined from the header of a SDMX-ML or -JSON data message.
- Except for :data:`.AllDimensions`, each row and column of the returned data frame contains multiple observations, so attributes cannot be included without ambiguity about which observation(s) have the attribute.
  In these cases, attributes are omitted; use `rtype` = 'rows' to retrieve them.

With the argument `rtype` = 'rows' (the default), data are *always* returned with one row per observation.


.. _howto-convert:

Convert SDMX data to other formats
----------------------------------

Pandas supports output to `many popular file formats <http://pandas.pydata.org/pandas-docs/stable/user_guide/io.html>`_.
Call these methods on the objects returned by :meth:`~sdmx.to_pandas`.
For instance::

    msg = sdmx.read_sdmx('data.xml')
    sdmx.to_pandas(msg).to_excel('data.xlsx')


pandaSDMX 0.9 could be used with `odo <https://github.com/blaze/odo>`_ by registering methods for discovery and conversion::

    import odo
    from odo.utils import keywords
    import pandas as pd
    from toolz import keyfilter
    import toolz.curried.operator as op

    class PandaSDMX(object):
        def __init__(self, uri):
            self.uri = uri

    @odo.resource.register(r'.*\.sdmx')
    def _resource(uri, **kwargs):
        return PandaSDMX(uri)

    @odo.discover.register(PandaSDMX)
    def _discover(obj):
        return odo.discover(sdmx.to_pandas(sdmx.read_sdmx(obj.uri)))

    @odo.convert.register(pd.DataFrame, PandaSDMX)
    def _convert(obj, **kwargs):
        msg = sdmx.read_sdmx(obj.uri)
        return sdmx.to_pandas(
            msg, **keyfilter(op.contains(keywords(write)), kwargs)
        )

.. deprecated:: 1.0

   odo `appears unmaintained <https://github.com/blaze/odo/issues/619>`_ since about 2016, so :mod:`sdmx` no longer provides built-in registration.

.. versionadded:: 0.4

   :meth:`sdmx.odo_register` was added, providing automatic registration.
