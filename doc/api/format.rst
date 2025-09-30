.. _format:

Standard formats
****************

The SDMX Information Model provides terms and concepts for data and metadata,
but does not specify how that (meta)data is stored, represented, or serialized.
Other parts of the SDMX standard describe formats for storing data, metadata, and structures.

:mod:`sdmx.format` captures information about these formats,
including their versions and options/parameters.
This information is used across other modules including :mod:`sdmx.reader`,
:mod:`sdmx.client`, and :mod:`sdmx.writer`.

In general, the :mod:`sdmx` package:

- **reads** most :ref:`sdmx-csv`, :ref:`sdmx-json` 1.0, and :ref:`sdmx-ml` messages;
  see details in the individual sections below and the linked :mod:`.reader` submodules.
- **writes** certain :ref:`sdmx-csv` and :ref:`sdmx-ml` formats;
  see details below and the linked :ref:`.writer` submodules.
- is **tested** using collected specimens of messages in various formats,
  stored in the `khaeru/sdmx-test-data <https://github.com/khaeru/sdmx-test-data/>`_ Git repository.
  These are used to check that the code functions as intended,
  but can also be viewed to understand the data formats.

.. automodule:: sdmx.format
   :members:
   :exclude-members: Version, f
   :undoc-members:
   :show-inheritance:

   .. autosummary::
      
      MEDIA_TYPES
      Flag
      MediaType
      list_media_types

.. _sdmx-csv:

SDMX-CSV
--------

Reference: https://github.com/sdmx-twg/sdmx-csv;
see in particular the file `sdmx-csv-field-guide.md <https://github.com/sdmx-twg/sdmx-csv/blob/v2.0.0/data-message/docs/sdmx-csv-field-guide.md>`_.

Based on Comma-Separated Value (CSV).
The SDMX-CSV *format* is versioned differently from the overall SDMX *standard*:

- `SDMX-CSV 1.0 <https://github.com/sdmx-twg/sdmx-csv/tree/v1.0>`__ corresponds to SDMX 2.1.
  It supports only data and metadata, not structures.
  SDMX-CSV 1.0 files are recognizable by the header ``DATAFLOW`` in the first column of the first row.

  .. versionadded:: 2.9.0

     Support for *writing* SDMX-CSV 1.0.
     See :mod:`.writer.csv`.

  :mod:`sdmx` does not currently support *reading* SDMX-CSV 1.0.

- `SDMX-CSV 2.0.0 <https://github.com/sdmx-twg/sdmx-csv/tree/v2.0.0>`_ corresponds to SDMX 3.0.0.
  The format differs from and is not backwards compatible with SDMX-CSV 1.0.
  SDMX-CSV 2.0.0 files are recognizable by the header ``STRUCTURE`` in the first column of the first row.

  :mod:`.reader.csv` supports reading SDMX-CSV 2.0.0.

  .. versionadded:: 2.19.0

     Initial support for reading SDMX-CSV 2.0.0.

  :mod:`.writer.csv` supports writing SDMX-CSV 2.0.0.
  Currently, only :attr:`Keys.none` is supported;
  passing any other value raises :class:`ValueError`.

  .. versionadded:: 2.23.0

     Initial support for writing SDMX-CSV 2.0.0.

.. automodule:: sdmx.format.csv.common
   :members:

.. automodule:: sdmx.format.csv.v1
   :members:

.. automodule:: sdmx.format.csv.v2
   :members:

.. _sdmx-json:

SDMX-JSON
---------

Reference: https://github.com/sdmx-twg/sdmx-json

Based on JavaScript Object Notation (JSON).
The SDMX-JSON *format* is versioned differently from the overall SDMX *standard*:

- SDMX-JSON 1.0 corresponds to SDMX 2.1.
  It supports only data and not structures or metadata.
- SDMX-JSON 2.0.0 corresponds to SDMX 3.0.0.
  It adds support for structures.

- See :mod:`.reader.json`.

.. versionadded:: 0.5

   Support for reading SDMX-JSON 1.0.

.. automodule:: sdmx.format.json
   :members:

.. _sdmx-ml:

SDMX-ML
-------

Reference: https://github.com/sdmx-twg/sdmx-ml

Based on eXtensible Markup Language (XML).
SDMX-ML can represent every class and property in the IM.

- An SDMX-ML document contains exactly one :class:`.Message`.
  See :mod:`sdmx.message` for the different classes of Messages and their attributes.
- See :mod:`.reader.xml.v21`, :mod:`.reader.xml.v30`, :mod:`.writer.xml`.

.. versionadded:: 2.11.0

   Support for reading SDMX-ML 3.0.0.
.. automodule:: sdmx.format.xml
   :members:
   :exclude-members: validate_xml

.. automodule:: sdmx.format.xml.common
   :members:
   :exclude-members: install_schemas, validate_xml

Format API
==========

.. automodule:: sdmx.format.common
   :members:
