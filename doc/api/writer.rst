.. currentmodule:: sdmx.writer

Writer/convert :mod:`sdmx` objects
**********************************

The term **write** refers to both:

- Converting :mod:`sdmx.message` and :mod:`sdmx.model` objects to the SDMX standard file formats.
- Converting :mod:`sdmx.model` objects to :mod:`pandas` objects.

.. _writer-csv:

``writer.csv``: Write to SDMX-CSV
=================================

.. versionadded:: 2.9.0

See :func:`.to_csv`.

.. automodule:: sdmx.writer.csv
   :members:
   :exclude-members: to_csv
   :show-inheritance:

.. _writer-pandas:

``writer.pandas``: Convert to ``pandas`` objects
================================================

.. currentmodule:: sdmx.writer.pandas

.. versionchanged:: 1.0

   :meth:`sdmx.to_pandas` handles all types of objects, replacing the earlier, separate ``data2pandas`` and ``structure2pd`` writers.

:func:`.to_pandas` implements a dispatch pattern according to the type of *obj*.
Some of the internal methods take specific arguments and return varying values.
These arguments can be passed to :func:`.to_pandas` when `obj` is of the appropriate type:

.. autosummary::
   sdmx.writer.pandas.write_dataset
   sdmx.writer.pandas.write_datamessage
   sdmx.writer.pandas.write_itemscheme
   sdmx.writer.pandas.write_structuremessage
   sdmx.writer.pandas.DEFAULT_RTYPE

Other objects are converted as follows:

:class:`.Component`
   The :attr:`~.Concept.id` attribute of the :attr:`~.Component.concept_identity` is returned.

:class:`.DataMessage`
   The :class:`.DataSet` or data sets within the Message are converted to pandas objects.
   Returns:

   - :class:`pandas.Series` or :class:`pandas.DataFrame`, if `obj` has only one data set.
   - list of (Series or DataFrame), if `obj` has more than one data set.

:class:`.dict`
   The values of the mapping are converted individually.
   If the resulting values are :class:`str` or Series *with indexes that share the same name*, then they are converted to a Series, possibly with a :class:`pandas.MultiIndex`.
   Otherwise, a :class:`.DictLike` is returned.

:class:`.DimensionDescriptor`
   The :attr:`~.DimensionDescriptor.components` of the DimensionDescriptor are written.

:class:`list`
   For the following *obj*, returns Series instead of a :class:`list`:

   - a list of :class:`Observation <.BaseObservation>`: the Observations are written using :meth:`write_dataset`.
   - a list with only 1 :class:`.DataSet` (e.g. the :attr:`~.DataMessage.data` attribute of :class:`.DataMessage`): the Series for the single element is returned.
   - a list of :class:`.SeriesKey`: the key values (but no data) are returned.

:class:`.NameableArtefact`
   The :attr:`~.NameableArtefact.name` attribute of `obj` is returned.

.. automodule:: sdmx.writer.pandas
   :members: DEFAULT_RTYPE, write_dataset, write_datamessage, write_itemscheme, write_structuremessage

.. todo::
   Support selection of language for conversion of
   :class:`InternationalString <sdmx.model.InternationalString>`.

``writer.xml``: Write to SDMX-ML
================================

.. versionadded:: 1.1

See :func:`.to_xml`.

.. automodule:: sdmx.writer.xml
   :members:
   :exclude-members: to_xml
   :show-inheritance:

Writer API
==========

.. currentmodule:: sdmx.writer

.. automodule:: sdmx.writer
   :members:
   :exclude-members: to_pandas, to_xml

.. autoclass:: sdmx.writer.base.BaseWriter
   :members:
