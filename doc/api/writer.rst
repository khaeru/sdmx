.. currentmodule:: sdmx.writer

Write standard formats
**********************

The term **write** means to convert :mod:`sdmx.message` and :mod:`sdmx.model` objects
specifically to the standard :doc:`/api/format`.
See :doc:`/api/convert` for conversion to data structures *not* described by the standards.

.. _writer-csv:

``writer.csv``: Write SDMX-CSV
==============================

.. versionadded:: 2.9.0

See :func:`.to_csv`.

.. automodule:: sdmx.writer.csv
   :members:
   :exclude-members: to_csv
   :show-inheritance:

.. _writer-xml:

``writer.xml``: Write SDMX-ML
=============================

.. versionadded:: 1.1

See :func:`.to_xml`.

.. automodule:: sdmx.writer.xml
   :members:
   :exclude-members: to_xml
   :show-inheritance:

Writer API
==========

.. automodule:: sdmx.writer.base
   :members:

