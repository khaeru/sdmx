Generate SDMX-ML from Python objects
************************************

:mod:`sdmx` was developed to retrieve SDMX-formatted data from web services and convert it to :mod:`pandas` objects.

The opposite—creating SDMX messages from Python or pandas objects—is also possible.
(Helper code to simplify this process is still a :doc:`planned future development </dev>`.)
This page gives a minimal demonstration.

Create some example data
========================

This data has:

- 8 *observations*.
- 2 *dimensions* with the identifiers (IDs) "TIME_DETAIL" and "REF_AREA".
- 1 *attribute* with the ID "UNIT_MEASURE".
- The measure—i.e. the quantity for which each observation provides a single value—has the generic ID "OBS_VALUE".

We store the data in a :class:`pandas.DataFrame`, with each row corresponding to one observation.
For example, the first observation has:

- Dimension values TIME_DETAIL=2016, REF_AREA=1.
  These are the **key** for the observation.
- The value "PT" for the UNIT_MEASURE attribute.
- A value of 50 for the primary measure.

.. ipython:: python

    import pandas as pd

    # List of dimensions
    D = ["TIME_DETAIL", "REF_AREA"]
    # List of measures
    M = ["OBS_VALUE"]
    # List of attributes
    A = ["UNIT_MEASURE"]

    # Keys, attributes, and values together in a single data frame
    data = pd.DataFrame(
        columns=D + M + A,
        data=[
            [2016, 1, 50, "PT"],
            [2017, 1, 60, "PT"],
            [2016, 2, 70, "PT"],
            [2017, 2, 80, "PT"],
            [2016, 1, 5000, "USD"],
            [2017, 1, 6000, "USD"],
            [2016, 2, 7000, "USD"],
            [2017, 2, 8000, "USD"],
        ],
    )
    data

Create a data structure definition (DSD)
========================================

The module :mod:`sdmx.model` contains the classes needed to describe the structure of this data set.
A DSD collects objects that describe the structure of the data.
There are different classes to describe dimensions, measures, and attributes.

.. ipython:: python

    import sdmx
    from sdmx.model.v21 import (
        DataStructureDefinition,
        Dimension,
        PrimaryMeasure,
        DataAttribute,
    )

    # Create an empty DSD
    dsd = DataStructureDefinition(id="CUSTOM_DSD")

    # Add 1 Dimension object to the DSD for each dimension of the data.
    # Dimensions must have a explicit order for make_key(), below.
    for order, id in enumerate(D):
        dsd.dimensions.append(Dimension(id=id, order=order))

    # `A` only has 1 element, but this code will work with 2 or more.
    for id in A:
        dsd.attributes.append(DataAttribute(id=id))

    for id in M:
        dsd.measures.append(PrimaryMeasure(id=id))

    # No longer needed
    del D, M, A

.. note:: This is a minimal example, so we don't further describe the structure, even though :mod:`sdmx.model` offers the full SDMX information model.

   We could, for instance, use a :class:`.Codelist` to add internationalized names, annotations, and other information to the codes "PT" and "USD" used for the "UNIT_MEASURE" attribute, and thus restrict the values of this attribute to the codes in that list.

   Or, we could add :class:`.Concept` objects to give a full description of what is meant by "REF_AREA"—regardless of whether it appears as a dimension or an attribute.

Populate a data set with observations
=====================================

The next step is to convert the data frame to :class:`Observation <.BaseObservation>` objects.
We define a new function, ``make_obs``, that operates on one row of the data frame.
The function generates a single Observation object by using the different columns as key values (for dimensions), attributes, or the observation value, as appropriate.

.. ipython:: python

    from sdmx.model.v21 import Key, AttributeValue, Observation

    # `key` is a Key that gives values for each dimension.
    # `attrs` is a dictionary of attribute values (here, only 1).
    # `value_for` refers to the measure.
    # `value` is the observation value for that measure.
    def make_obs(row):
        key = dsd.make_key(Key, row[[d.id for d in dsd.dimensions]])
        attrs = {
          a.id: AttributeValue(value_for=a, value=row[a.id])
          for a in dsd.attributes
        }
        return Observation(
             dimension=key,
             attached_attribute=attrs,
             value_for=dsd.measures[0],
             value=row[dsd.measures[0].id],
        )


.. note:: Because the DSD is a complete description of the structure of the data, notice that ``make_obs`` can use its properties to retrieve the IDs for dimensions, attributes, and the primary measure.

   The variables ``D``, ``M``, and ``A`` were already deleted and aren't used anymore.

Next, we use the built-in method :meth:`pandas.DataFrame.apply` to run this function on each row of ``data``.

.. ipython:: python

    # Convert each row of `data` to an Observation
    # apply() returns a pd.Series; convert to a list
    observations = data.apply(make_obs, axis=1).to_list()

This list of Observation objects can now be used to create :class:`Datasets <.DataSet>`.

Because of the structure of our ``data``, there are only 4 unique keys for 8 observations.
For instance, the key TIME_DETAIL=2016, REF_AREA=1 appears *twice*, each time with a different value for the UNIT_MEASURE attribute.
The SDMX information model requires that every observation in a data set has a *unique* key.
We meet this requirement by creating two data sets, so that each data set contains a set of unique keys.

.. ipython:: python

    from sdmx.model.v21 import DataSet

    # Only the Observations with UNIT_MEASURE="PT"
    ds1 = DataSet(structured_by=dsd, obs=observations[:4])
    ds1

    # Observations with UNIT_MEASURE="USD"
    ds2 = DataSet(structured_by=dsd, obs=observations[4:])
    ds2

The DSD is also connected to each data set.

Encapsulate in messages and write to file
=========================================

SDMX files always contain complete *messages* with either data or structure.
To write the ``ds1`` and ``ds2`` objects to file, we need to enclose them in a message object.

An SDMX data message doesn't refer to a DSD directly, but to a data *flow* definition (DFD), which in turn refers to the DSD.
We create a DFD as well.

.. ipython:: python

    from sdmx.model.v21 import DataflowDefinition
    from sdmx.message import DataMessage

    # The DFD points to the DSD
    dfd = DataflowDefinition(id="CUSTOM_DFD", structure=dsd)

    # The data message contains the data set, and points to the data flow
    msg1 = DataMessage(data=[ds1, ds2], dataflow=dfd)

    # Write in SDMX-ML (XML) format
    with open("data-message.xml", "wb") as f:
        f.write(sdmx.to_xml(msg1))

We also write the DFD and DSD to file.
This step is not required: :mod:`sdmx` could infer these when reading :file:`data-message.xml`.
However, the very purpose of the SDMX standard is to enable good practice, to be explicit and unambiguous about how data is structured and what it means.

.. ipython:: python

    from sdmx.message import StructureMessage

    # Structure messages can contain many instances of several kinds
    # of structure objects. See the documentation.
    msg2 = StructureMessage(
        dataflow={dfd.id: dfd},
        structure={dsd.id: dsd},
    )
    with open("structure-message.xml", "wb") as f:
        f.write(sdmx.to_xml(msg2))

Check the results
=================

We read the data from the files just generated.

.. ipython:: python

    # Delete references to all the objects just created
    del msg1, msg2, ds1, ds2, dfd, dsd, observations

    # Re-read from files
    msg3 = sdmx.read_sdmx("structure-message.xml")
    msg4 = sdmx.read_sdmx(
      "data-message.xml", dsd=msg3.structure["CUSTOM_DSD"]
    )

    # Convert to a data frame, including attributes in a column
    dfs = sdmx.to_pandas(msg4, attributes="o")
    dfs

:func:`.to_pandas` converts each data set in the message to a separate :mod:`pandas` object with a unique :class:`pandas.MultiIndex`, so this call returns a list containing two data frames.

We can also combine these data frames into a single one, with a non-unique index, and then use :meth:`pandas.DataFrame.reset_index` to recover the initial structure:

.. ipython:: python

    pd.concat(dfs).reset_index()

.. note:: Simplifying the process of authoring different kinds of SDMX objects and messages is a priority enhancement for :mod:`sdmx`.
   Contributions are welcome; see :doc:`/dev`.
