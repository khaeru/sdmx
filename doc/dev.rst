Development
***********

This page describes the development of :mod:`sdmx`.
Contributions are welcome!

- For current development priorities, see the list of `GitHub milestones <https://github.com/khaeru/sdmx/milestones>`_ and issues/PRs targeted to each.
- For wishlist features, see issues on GitHub tagged `‘enh’ <https://github.com/khaeru/sdmx/labels/enh>`_ or `‘wishlist’ <https://github.com/khaeru/sdmx/labels/wishlist>`_.

.. contents::
   :local:
   :backlinks: none

Code style
==========

- Apply the following to new or modified code::

    isort -rc . && black . && mypy . && flake8

  Respectively, these:

  - **isort**: sort import lines at the top of code files in a consistent way, using `isort <https://pypi.org/project/isort/>`_.
  - **black**: apply `black <https://black.readthedocs.io>`_ code style.
  - **mypy**: check typing using `mypy <https://mypy.readthedocs.io>`_.
  - **flake8**: check code style against `PEP 8 <https://www.python.org/dev/peps/pep-0008>`_ using `flake8 <https://flake8.pycqa.org>`_.

- Follow `the 7 rules of a great Git commit message <https://chris.beams.io/posts/git-commit/#seven-rules>`_.
- Write docstrings in the `numpydoc <https://numpydoc.readthedocs.io/en/latest/format.html>`_ style.

.. _testing:

Test specimens
==============

.. versionadded:: 2.0

A variety of *specimens*—example files from real web services, or published with the standards—are used to test that :mod:`sdmx` correctly reads and writes the different SDMX message formats.
Since v2.0, specimens are stored in the separate `sdmx-test-data <https://github.com/khaeru/sdmx-test-data>`_ repository.

Running the test suite requires these files.
To retrieve them, use one of the following methods:

1. Obtain the files by one of two methods:

   a. Clone ``khaeru/sdmx-test-data``::

       $ git clone git@github.com:khaeru/sdmx-test-data.git

   b. Download https://github.com/khaeru/sdmx-test-data/archive/master.zip

2. Indicate where pytest can find the files, by one of two methods:

   a. Set the `SDMX_TEST_DATA` environment variable::

       # Set the variable only for one command
       $ SDMX_TEST_DATA=/path/to/files pytest

       # Export the variable to the environment
       $ export SDMX_TEST_DATA
       $ pytest

   b. Give the option ``--sdmx-test-data=<PATH>`` when invoking pytest::

       $ pytest --sdmx-test-data=/path/to/files

The files are:

- Arranged in directories with names matching particular sources in :file:`sources.json`.
- Named with:

  - Certain keywords:

    - ``-structure``: a structure message, often associated with a file with a similar name containing a data message.
    - ``ts``: time-series data, i.e. with a TimeDimensions at the level of individual Observations.
    - ``xs``: cross-sectional data arranged in other ways.
    - ``flat``: flat DataSets with all Dimensions at the Observation level.
    - ``ss``: structure-specific data messages.

  - In some cases, the query string or data flow/structure ID as the file name.
  - Hyphens ``-`` instead of underscores ``_``.


Releasing
=========

Before releasing, check:

- https://github.com/khaeru/sdmx/actions?query=workflow:pytest+branch:master to ensure that the push and scheduled builds are passing.
- https://readthedocs.org/projects/sdmx1/builds/ to ensure that the docs build is passing.

Address any failures before releasing.

1. Edit :file:`doc/whatsnew.rst`.
   Comment the heading "Next release", then insert another heading below it, at the same level, with the version number and date.
   Make a commit with a message like "Mark vX.Y.Z in doc/whatsnew".

2. Tag the version as a release candidate, i.e. with a ``rcN`` suffix, and push::

    $ git tag v1.2.3rc1
    $ git push --tags master

3. Check:

   - at https://github.com/khaeru/sdmx/actions?query=workflow:publish that the workflow completes: the package builds successfully and is published to TestPyPI.
   - at https://test.pypi.org/project/sdmx1/ that:

      - The package can be downloaded, installed and run.
      - The README is rendered correctly.

   Address any warnings or errors that appear.
   If needed, make a new commit and go back to step (2), incrementing the rc number.

4. **Optional.** This step (but *not* step (2)) can also be performed directly on GitHub; see (5), next.
   Tag the release itself and push::

    $ git tag v1.2.3
    $ git push --tags master

5. Visit https://github.com/khaeru/sdmx/releases and mark the new release: either using the pushed tag from (4), or by creating the tag and release simultaneously.

6. Check at https://github.com/khaeru/sdmx/actions?query=workflow:publish and https://pypi.org/project/sdmx1/ that the distributions are published.


Internal code reference
=======================

``testing``: Testing utilities
------------------------------

.. automodule:: sdmx.testing
   :members:
   :undoc-members:
   :show-inheritance:

``util``: Utilities
-------------------
.. automodule:: sdmx.util
   :noindex:
   :members: BaseModel, summarize_dictlike, validate_dictlike
   :undoc-members:
   :show-inheritance:


Inline TODOs
============

.. todolist::
