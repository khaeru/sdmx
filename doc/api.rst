API reference
*************

Some parts of the API are described on separate pages:

.. toctree::
   :hidden:

   api/model
   api/format
   api/convert
   api/reader
   api/writer

- :mod:`sdmx.model`: :doc:`api/model`.
- :mod:`sdmx.format`: :doc:`api/format`.
- :mod:`sdmx.convert`: :doc:`api/convert`.
- :mod:`sdmx.reader`: :doc:`api/reader`.
- :mod:`sdmx.writer`: :doc:`api/writer`.
- :mod:`sdmx.source` on the page :doc:`sources`.

See also the :doc:`implementation`.

On this page:

.. contents::
   :class: this-will-duplicate-information-and-it-is-still-useful-here
   :local:
   :depth: 1
   :backlinks: none

Top-level methods and classes
=============================

.. automodule:: sdmx
   :members:

   .. autosummary::

      Client
      Resource
      add_source
      get_source
      install_schemas
      list_sources
      log
      read_sdmx
      read_url
      to_csv
      to_pandas
      to_xml
      to_sdmx
      validate_xml

``compare``: Compare SDMX artefacts
===================================

.. currentmodule:: sdmx.compare

.. automodule:: sdmx.compare
   :members:
   :show-inheritance:

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

.. automodule:: sdmx.session
   :members: Session, ResponseIO

``urn``: Uniform Resource Names (URNs) for SDMX objects
=======================================================

.. automodule:: sdmx.urn
   :members:


Utilities and internals
=======================

.. currentmodule:: sdmx.tools

.. automodule:: sdmx.tools
   :members:
   :show-inheritance:

.. currentmodule:: sdmx.util

.. automodule:: sdmx.util
   :members:
   :show-inheritance:

.. currentmodule:: sdmx.types

.. automodule:: sdmx.types
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
