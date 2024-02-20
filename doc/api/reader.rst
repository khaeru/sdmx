Read SDMX file formats
**********************

SDMX-ML
=======

.. currentmodule:: sdmx.reader.xml

:mod:`sdmx.reader.xml` supports the several types of SDMX-ML messages.

Implementation details:

- The collections of :class:`.StructureMessage` (e.g. :attr:`.StructureMessage.codelist`) are implemented by :mod:`sdmx` as :class:`.DictLike`, with :class:`str` keys, for convenience; the standard would imply these could be other collections, such as a simple :class:`list`.
  The format of the keys in each collection depends on the content of the message parsed by :mod:`.reader.xml`:

  - Simply ``{object.id}`` (:attr:`.IdentifiableArtefact.id`) of the contained objects, if these are unique;
  - Otherwise ``{maintainer.id}:{object.id}`` (using the :class:`.Agency` id) if these are unique;
  - Otherwise ``{maintainer.id}:{object.id}({object.version})`` (using the :attr:`.VersionableArtefact.version`).

  This ensures that all objects in a parsed message are accessible.

.. automodule:: sdmx.reader.xml
   :members:

.. currentmodule:: sdmx.reader.xml.v21

.. automodule:: sdmx.reader.xml.v21
   :members:

.. currentmodule:: sdmx.reader.xml.v30

.. automodule:: sdmx.reader.xml.v30
   :members:

SDMX-JSON
=========

.. currentmodule:: sdmx.reader.json

.. automodule:: sdmx.reader.json

.. autoclass:: sdmx.reader.json.Reader
    :members:
    :undoc-members:

SDMX-CSV
=========

.. currentmodule:: sdmx.reader.csv

.. autoclass:: sdmx.reader.csv.Reader
    :members:
    :undoc-members:


Reader API
==========

.. currentmodule:: sdmx.reader

.. automodule:: sdmx.reader
   :members:

.. autoclass:: sdmx.reader.base.BaseReader
   :members:
