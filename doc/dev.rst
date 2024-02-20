Development
***********

This page describes the development of :mod:`sdmx`.
Contributions are welcome!

- For current development priorities, see the list of `GitHub milestones <https://github.com/khaeru/sdmx/milestones>`_ and issues/PRs targeted to each.
- For wishlist features, see issues on GitHub tagged `‘enh’ <https://github.com/khaeru/sdmx/labels/enh>`_ or `‘wishlist’ <https://github.com/khaeru/sdmx/labels/wishlist>`_.

.. _code-style:

Code style
==========

- This project uses, via `pre-commit <https://pre-commit.com>`_:

  - `ruff <https://beta.ruff.rs/docs/>`_ for code style and linting, including:

     - ensure `PEP 8 <https://www.python.org/dev/peps/pep-0008>`_ compliance, and
     - ensure a consistent order for imports (superseding `flake8 <https://flake8.pycqa.org>`_ and `isort <https://pypi.org/project/isort/>`_).
  - `mypy <https://mypy.readthedocs.io>`_ for static type checking.

  These **must** be applied to new or modified code.
  This can be done manually, or through code editor plug-ins.
  `Pre-commit hooks for git <https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks>`_ can be installed via:

  .. code-block:: shell

     pip install pre-commit
     pre-commit install

  These will ensure that each commit is compliant with the code style.

- The `pytest.yaml GitHub Actions workflow <https://github.com/khaeru/sdmx/actions/workflows/pytest.yaml>`_ checks code quality for pull requests and commits.
  This check **must** pass for pull requests to be merged.
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

   b. Download https://github.com/khaeru/sdmx-test-data/archive/main.zip

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

- https://github.com/khaeru/sdmx/actions?query=workflow:test+branch:main to ensure that the push and scheduled builds are passing.
- https://readthedocs.org/projects/sdmx1/builds/ to ensure that the docs build is passing.

Address any failures before releasing.

1. Create a new branch::

     $ git checkout -v release/X.Y.Z

2. Edit :file:`doc/whatsnew.rst`.
   Comment the heading "Next release", then insert another heading below it, at the same level, with the version number and date.

3. Make a commit with a message like "Mark vX.Y.Z in doc/whatsnew".

4. Tag the version as a release candidate, i.e. with a ``rcN`` suffix, and push::

    $ git tag vX.Y.ZrcN
    $ git push --tags --set-upstream origin release/X.Y.Z

5. Open a pull request with the title “Release vX.Y.Z” using this branch.
   Check:

   - at https://github.com/khaeru/sdmx/actions?query=workflow:publish that the workflow completes: the package builds successfully and is published to TestPyPI.
   - at https://test.pypi.org/project/sdmx1/ that:

      - The package can be downloaded, installed and run.
      - The README is rendered correctly.

   If needed, address any warnings or errors that appear and then continue from step (3), i.e. make (a) new commit(s) and tag, incrementing the release candidate number, e.g. from ``rc1`` to ``rc2``.

6. Merge the PR using the “rebase and merge” method.

7. (optional) Tag the release itself and push::

    $ git tag vX.Y.Z
    $ git push --tags origin main

   This step (but *not* step (3)) can also be performed directly on GitHub; see (7), next.

8. Visit https://github.com/khaeru/sdmx/releases and mark the new release: either using the pushed tag from (7), or by creating the tag and release simultaneously.

9. Check at https://github.com/khaeru/sdmx/actions?query=workflow:publish and https://pypi.org/project/sdmx1/ that the distributions are published.


Internal code reference
=======================

.. automodule:: sdmx.dictlike
   :noindex:
   :undoc-members:
   :show-inheritance:

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
   :undoc-members:
   :show-inheritance:


Inline TODOs
============

.. todolist::
