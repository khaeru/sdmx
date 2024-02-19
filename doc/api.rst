API reference
*************

Some parts of the API are described on separate pages:

.. toctree::
   :hidden:

   api/model
   api/reader
   api/writer

- :mod:`sdmx.model`: :doc:`api/model`.
- :mod:`sdmx.reader`: :doc:`api/reader`.
- :mod:`sdmx.writer`: :doc:`api/writer`.
- :mod:`sdmx.source` on the page :doc:`sources`.

See also the :doc:`implementation`.

Top-level methods and classes
=============================

.. automodule:: sdmx
   :members:

   .. autosummary::

      Client
      Resource
      add_source
      list_sources
      log
      read_sdmx
      read_url
      to_csv
      to_pandas
      to_xml

``format``: SDMX file formats
=============================

.. automodule:: sdmx.format
   :members:
   :exclude-members: Version
   :undoc-members:
   :show-inheritance:

   This information is used across other modules including :mod:`sdmx.reader`,
   :mod:`sdmx.client`, and :mod:`sdmx.writer`.

SDMX-JSON
---------

.. automodule:: sdmx.format.json
   :members:

SDMX-ML
-------

.. automodule:: sdmx.format.xml
   :members:

``message``: SDMX messages
==========================

.. automodule:: sdmx.message
   :members:
   :undoc-members:
   :show-inheritance:

``rest``: SDMX-REST standard
============================

.. automodule:: sdmx.rest
   :members:
   :exclude-members: Resource
   :show-inheritance:

``rest.v21``
------------

.. automodule:: sdmx.rest.v21
   :members:
   :show-inheritance:

``rest.v30``
------------

.. automodule:: sdmx.rest.v30
   :members:
   :show-inheritance:


``session``: HTTP sessions and responses
========================================
.. autoclass:: sdmx.session.Session
.. autoclass:: sdmx.session.ResponseIO


``urn``: Uniform Resource Names (URNs) for SDMX objects
=======================================================
.. automodule:: sdmx.urn
   :members:


Utilities and internals
=======================

.. currentmodule:: sdmx.util

.. automodule:: sdmx.util
   :members:
   :show-inheritance:


:class:`.DictLike` collections
------------------------------

.. currentmodule:: sdmx.dictlike

.. automodule:: sdmx.dictlike
   :members:
   :show-inheritance:


Structure expressions in :class:`.Item` descriptions
----------------------------------------------------

.. currentmodule:: sdmx.util.item_structure

.. automodule:: sdmx.util.item_structure
   :members:
   :show-inheritance:

   .. autosummary::

      parse_item_description
      parse_item
      parse_all

   .. note::

      The code in this module does *not* perform calculations or operations on data using the parsed structure expressions.
      User code **should** use the returned information to determine which operations should be performed.
