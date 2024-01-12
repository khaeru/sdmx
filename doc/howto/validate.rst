Validate SDMX-ML against official schemas
*****************************************

:mod:`sdmx` is capable of generating XML for all kinds of SDMX components. When communicating with remote services though, only valid SDMX-ML messages can be sent.
To help ensure your generated XML complies with the standard you can call :func:`.validate_xml`.

Validation requires having a copy of the `official schema <https://github.com/sdmx-twg/>`_ files available.
To help make this easier, you can use :func:`.install_schemas`, which will cache a local copy for use in validation.

Cache schema files
==================

Installation of the schemas defaults to v2.1 format. For SDMX v3.0 you need to supply the version string.

.. note:: This only needs to be run once for each SDMX-ML version.

.. ipython:: python

    import sdmx
    sdmx.install_schemas()
    # or
    sdmx.install_schemas(version="3.0")

The schema files will be downloaded and placed in your local cache directory.

Validate SDMX-ML messages
=========================

Generate an SDMX-ML message, perhaps by following :doc:`create`.
Once you have a file on disk that has an SDMX-ML message it can be validated by running :func:`.validate_xml`.
These instructions will use the samples provided by the `SDMX technical working group <https://github.com/sdmx-twg/sdmx-ml-v2_1>`_.

.. code-block:: python

    >>> import sdmx
    >>> sdmx.validate_xml("samples/common/common.xml")
    True
    >>> sdmx.validate_xml("samples/demography/demography.xml")
    True

Validating SDMX v3.0 messages requires a version parameter to be supplied.

.. code-block:: python

    >>> sdmx.validate_xml("samples/Codelist/codelist.xml", version="3.0")

Invalid messages will return ``False``. You will also see a log message to help in tracing the problem::

    Element '{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common}Annotations': This element is not expected.
    Expected is one of ( {http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common}Description,
    {http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure}Structure )., line 17
