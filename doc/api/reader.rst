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


.. currentmodule:: sdmx.reader.csv

SDMX-CSV
=========

:mod:`sdmx.reader.csv` supports SDMX-CSV 2.0.0, corresponding to SDMX 3.0.0.
See :ref:`sdmx-csv` for differences between versions of the SDMX-CSV file format.

Implementation details:

- :meth:`.Reader.inspect_header` inspects the header line in the CSV input and constructs a set of :class:`~.csv.Handler` instances, one for each field appearing in the particular file.
  Some of these handlers do actually process the contents of the field, but silently discard it; for example, when ``labels="name"``, the name fields are not processed.
- :meth:`.Reader.handle_row` is applied to every record in the CSV input.
  Each Handler is applied to its respective field.
  Every :meth:`.handle_row` call constructs a single :class:`~.v30.Observation`.
- :meth:`.Reader.read_message` assembles the resulting observations into one or more :class:`DataSets <.common.BaseDataSet>`.
  SDMX-CSV 2.0.0 specifies a mix of codes such as "I" (:attr:`.ActionType.information`) and "D" (:attr:`.ActionType.delete`) in the "ACTION" field for each observation in the same file, whereas the SDMX IM specifies that :attr:`~.BaseDataSet.action` is an attribute of an entire DataSet.
  :class:`~.csv.Reader` groups all observations into 1 or more DataSet instances, according to their respective "ACTION" field values.

Currently :mod:`.reader.csv` has the following limitations:

- :meth:`.Reader.read_message` generates SDMX 3.0.0 (:mod:`.model.v30`) artefacts such as :class:`.v30.DataSet`, since these correspond to the supported SDMX-CSV 2.0.0 format.
  It is not currently supported to generate SDMX 2.1 artefacts such as :class:`.v21.DataSet`.
- Currently only a single :class`.v30.Dataflow` or :class:`.v30.DataStructureDefinition` can be supplied to :meth:`.Reader.read_message`.
  The SDMX-CSV 2.0.0 format supports mixing data flows and data structures in the same message.
  Such messages can be read with :mod:`sdmx`, but the resulting data sets will only correspond to the given data flow.

.. automodule:: sdmx.reader.csv
   :members:
   :undoc-members:
   :show-inheritance:

Reader API
==========

.. currentmodule:: sdmx.reader

.. automodule:: sdmx.reader
   :members:

.. autoclass:: sdmx.reader.base.Converter
   :members:

.. autoclass:: sdmx.reader.base.BaseReader
   :members:
