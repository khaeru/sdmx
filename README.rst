sdmx: Statistical data and metadata exchange
********************************************

.. image:: https://github.com/khaeru/sdmx/actions/workflows/pytest.yaml/badge.svg
   :target: https://github.com/khaeru/sdmx/actions
   :alt: Status badge for the "pytest" continuous integration workflow
.. image:: https://codecov.io/gh/khaeru/sdmx/branch/main/graph/badge.svg
   :target: https://codecov.io/gh/khaeru/sdmx
   :alt: Codecov test coverage badge
.. image:: https://readthedocs.org/projects/sdmx1/badge/?version=latest
   :target: https://sdmx1.readthedocs.io/en/latest
   :alt: Documentation status badge
.. image:: https://img.shields.io/pypi/v/sdmx1.svg
   :target: https://pypi.org/project/sdmx1
   :alt: PyPI version badge
.. image:: https://img.shields.io/badge/services-status-informational
   :target: https://khaeru.github.io/sdmx/
   :alt: Status of supported service endpoints

`Source code @ Github <https://github.com/khaeru/sdmx/>`_ —
`Authors <https://github.com/khaeru/sdmx/graphs/contributors>`_

`sdmx` is an `Apache 2.0-licensed <LICENSE>`_ Python package that implements `SDMX <http://www.sdmx.org>`_ 2.1 (`ISO 17369:2013 <https://www.iso.org/standard/52500.html>`_) and 3.0, a format for exchange of **statistical data and metadata** used by national statistical agencies, central banks, and international organisations.

`sdmx` can be used to:

- explore the data available from `data providers <https://sdmx1.rtfd.io/en/latest/sources.html>`_ such as the World Bank, International Monetary Fund, Eurostat, OECD, and United Nations;
- parse data and metadata in SDMX-ML (XML) or SDMX-JSON formats—either:

  - from local files, or
  - retrieved from SDMX web services, with query validation and caching;

- convert data and metadata into `pandas <https://pandas.pydata.org>`_ objects, for use with the analysis, plotting, and other tools in the Python data science ecosystem;
- apply the `SDMX Information Model <https://sdmx1.rtfd.io/en/latest/api.rst#api-model>`_ to your own data;

…and much more.


Documentation
-------------

See https://sdmx1.readthedocs.io/en/latest/ for the latest docs per the ``main`` branch, or https://sdmx1.readthedocs.io/en/stable/ for the most recent release.


License
-------

Copyright 2014–2023, `sdmx1 developers <https://github.com/khaeru/sdmx/graphs/contributors>`_

Licensed under the Apache License, Version 2.0 (the “License”); you may not use
these files except in compliance with the License. You may obtain a copy of the
License:

- from the file LICENSE included with the source code, or
- at http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an “AS IS” BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.


History
-------

`sdmx` is a fork of pandaSDMX_; in turn a fork of pysdmx_.
Many people from all over the world have generously contributed code and feedback.

.. _pandaSDMX: https://github.com/dr-leo/pandaSDMX
.. _pysdmx: https://github.com/widukind/pysdmx
