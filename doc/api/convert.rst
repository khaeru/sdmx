Convert from/to SDMX
********************

:mod:`sdmx.convert` and :mod:`sdmx.convert.common`
provide generic and extensible features for converting:

- from :mod:`sdmx.message` and :mod:`sdmx.model` objects
  to arbitrary Python data structures, or
- from arbitrary Python data structures to :mod:`sdmx` objects.

The included :mod:`sdmx.convert.pandas`, :class:`.PandasConverter`, and :func:`.to_pandas`
build on these features to provide conversion to types from the :mod:`pandas` package.
This conversion is **not described by the SDMX standards**;
in other words, it is particular to the :mod:`sdmx` package.

In contrast, submodules of :mod:`sdmx.writer`, :func:`.to_csv`, and :func:`.to_xml`
provide conversion to standard :doc:`/api/format`.

User code can also subclass :class:`~.common.Converter` or :class:`.DispatchConverter`
to convert to/from other Python types or non-standard formats.

.. module:: sdmx.convert

.. automodule:: sdmx.convert.common
   :members:

``convert.pandas``: Convert to ``pandas`` objects
=================================================

.. currentmodule:: sdmx.convert.pandas


.. autosummary::
   PandasConverter
   convert_dataset
   convert_datamessage
   convert_itemscheme
   convert_structuremessage

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
   The :attr:`~.DimensionDescriptor.components` of the DimensionDescriptor are converted.

:class:`list`
   For the following *obj*, returns Series instead of a :class:`list`:

   - a list of :class:`Observation <.BaseObservation>`:
     the Observations are converted using :func:`.convert_dataset`.
   - a list with only 1 :class:`DataSet <.BaseDataSet`
     (e.g. the :attr:`~.DataMessage.data` attribute of :class:`.DataMessage`):
     the Series for the single element is returned.
   - a list of :class:`.SeriesKey`: the key values (but no data) are returned.

:class:`.NameableArtefact`
   The :attr:`~.NameableArtefact.name` attribute of `obj` is returned.

.. todo::
   Support selection of language for conversion of
   :class:`InternationalString <sdmx.model.InternationalString>`.

Code reference
--------------

.. automodule:: sdmx.convert.pandas
   :members:
   :exclude-members: to_pandas
