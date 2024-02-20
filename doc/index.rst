Statistical Data and Metadata eXchange (SDMX) in Python
*******************************************************

:mod:`sdmx` (`‘sdmx1’ on PyPI <https://pypi.org/project/sdmx1>`_) is a Python implementation of the `SDMX <http://www.sdmx.org>`_  2.1 (`ISO 17369:2013 <https://www.iso.org/standard/52500.html>`_) and 3.0 standards for **Statistical Data and Metadata eXchange**.
The SDMX standards are developed and used by national statistical agencies, central banks, and international organisations.

:mod:`sdmx` can be used to:

- Explore and retrieve data available from SDMX-REST :doc:`web services <sources>` operated by providers including the World Bank, International Monetary Fund, Eurostat, OECD, and United Nations;
- Read and write data and metadata in file formats including SDMX-ML (XML), SDMX-JSON, and SDMX-CSV;
- Convert data and metadata into `pandas <http://pandas.pydata.org>`_ objects, for use with the analysis, plotting, and other tools in the Python data science ecosystem;
- Apply the :doc:`SDMX information model (IM) <implementation>` to structure and publish your own data;

…and much more.

Get started
===========

The SDMX standards are designed to be flexible enough to accommodate nearly *any* data.
To do this, they include a large number of abstract concepts for describing data, metadata, and their structure and relationships.
These are collectively called the **information model** (**IM**) of SDMX.

.. _not-the-standard:

The documentation you are reading does not (and could not) repeat full descriptions of the IM or other parts of the SDMX standards.
Instead, it focuses on the :doc:`precise, Pythonic, and useful implementation <implementation>` that this :mod:`sdmx` package aims to provide.

Detailed knowledge of the IM is not needed to use :mod:`sdmx`; see a :doc:`usage example in only 10 lines of code <example>` or a longer, narrative :doc:`walkthrough <walkthrough>`.
To learn about SDMX in more detail, use the :doc:`list of resources and references <resources>`, or read the :doc:`API documentation <api>` in detail.

.. toctree::
   :maxdepth: 1

   example
   install
   walkthrough


:mod:`sdmx` user guide
======================

.. toctree::
   :maxdepth: 2

   sources
   api
   implementation
   howto
   whatsnew
   dev


Contributing and getting help
=============================

- Ask usage questions (“How do I?”) on `Stack Overflow <https://stackoverflow.com/questions/tagged/python-sdmx+or+sdmx>`_ using the tags ``[sdmx] [python]``.
- Report bugs, suggest features, or view the source code on
  `GitHub <https://github.com/khaeru/sdmx>`_.
- The older `sdmx-python <https://groups.google.com/forum/?hl=en#!forum/sdmx-python>`_ Google Group may have answers for some questions.


.. toctree::

   resources
   glossary
   license

- :ref:`genindex`
