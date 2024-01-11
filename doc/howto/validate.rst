Validate SDMX-ML against official schemas
*****************************************

:mod:`sdmx` is capable of generating XML for all kinds of SDMX components. When communicating with remote services
though, only valid SDMX-ML messages can be sent. To help ensure your generated XML complies with the standard you can
call :func:`sdmx.validate_xml`.

Validation requires having a copy of the `official schema <https://github.com/sdmx-twg/sdmx-ml-v2_1>`_ files available.
To help make this easier, you can use :func:`sdmx.install_schemas`, which will cache a local copy for use in validation.

Cache schema files
==================

.. note:: This only needs to be run once.

.. ipython:: python
    import sdmx
    sdmx.install_schemas()
The schema files will be downloaded and placed in your local cache directory.

Validate SDMX-ML messages
=========================

Generate an SDMX-ML message, perhaps by following :doc:`create`. Once you have a file on disk that has an SDMX-ML
message it can be validated by running :func:`sdmx.validate_xml`. These instructions will use the samples provided by
the `SDMX technical working group <https://github.com/sdmx-twg/sdmx-ml-v2_1>`_.

.. code-block:: python
    import sdmx
    sdmx.validate_xml("samples/common/common.xml")
    True
    sdmx.validate_xml("samples/demography/demography.xml")
    True

Invalid messages will return ``False``. You will also see a log message to help in tracing the problem::

    Element '{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common}Annotations': This element is not expected.
    Expected is one of ( {http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common}Description,
    {http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure}Structure )., line 17
