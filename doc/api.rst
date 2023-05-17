API reference
=============

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
-----------------------------

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
-----------------------------

.. automodule:: sdmx.format
   :members:
   :undoc-members:
   :show-inheritance:

   This information is used across other modules including :mod:`sdmx.reader`,
   :mod:`sdmx.client`, and :mod:`sdmx.writer`.

SDMX-JSON
:::::::::

.. automodule:: sdmx.format.json
   :members:

SDMX-ML
:::::::

.. automodule:: sdmx.format.xml
   :members:

``message``: SDMX messages
--------------------------

.. automodule:: sdmx.message
   :members:
   :undoc-members:
   :show-inheritance:

``rest``: SDMX-REST standard
----------------------------

.. automodule:: sdmx.rest
   :members:
   :exclude-members: Resource
   :show-inheritance:


``session``: Access SDMX REST web services
------------------------------------------
.. autoclass:: sdmx.session.Session
.. autoclass:: sdmx.session.ResponseIO


``urn``: Uniform Resource Names (URNs) for SDMX objects
-------------------------------------------------------
.. automodule:: sdmx.urn
   :members:


``util``: Utilities
-------------------
.. automodule:: sdmx.util
   :members:
   :exclude-members: summarize_dictlike
   :show-inheritance:
