Ten-line usage example
======================

Suppose we want to analyze annual unemployment data for some European countries.
All we need to know in advance is the data provider: Eurostat.

:mod:`sdmx` makes it easy to search the directory of data flows, and the complete structural metadata about the datasets available through the selected dataflow.
(This example skips these steps; see :doc:`the walkthrough <walkthrough>`.)

The data we want is in a **data flow** with the identifier ‘UNE_RT_A’.
This dataflow references a **data structure definition** (**DSD**) that also has an ID ‘UNE_RT_A’.
The DSD, in turn, contains or references all the metadata describing data sets available through this dataflow: the concepts, things measured, dimensions, and lists of codes used to label each dimension.

.. ipython:: python

    import sdmx
    estat = sdmx.Client("ESTAT")

Download the metadata and expose:

.. ipython:: python

    metadata = estat.datastructure("UNE_RT_A", params=dict(references="descendants"))
    metadata

Explore the contents of some code lists:

.. ipython:: python

    for cl in "AGE", "UNIT":
        print(sdmx.to_pandas(metadata.codelist[cl]))

Next we download a **data set** containing a subset of the data from this data flow, structured by this DSD.
To obtain data on Greece, Ireland and Spain only, we use codes from the code list with the ID ‘GEO’ to specify a **key** for the dimension with the ID ‘geo’ (note the difference: SDMX IDs are case-sensitive).
We also use a **query parameter**, ‘startPeriod’, to limit the scope of the data returned:

.. ipython:: python

    resp = estat.data(
        "UNE_RT_A",
        key={"geo": "EL+ES+IE"},
        params={"startPeriod": "2007"},
    )

``resp`` is now a :class:`.DataMessage` object.
We use the :func:`sdmx.to_pandas` function to convert it to a :class:`pandas.Series`, then select on the ‘age’ dimension:

.. ipython:: python

    data = (
        sdmx.to_pandas(resp)
        .xs("Y15-74", level="age", drop_level=False)
    )

We can now explore the data set as expressed in a familiar pandas object.
First, show dimension names:

.. ipython:: python

    data.index.names


…and corresponding key values along these dimensions:

.. ipython:: python

    data.index.levels

Select some data of interest: show aggregate unemployment rates across ages ("Y15-74" on the ‘age’ dimension) and sexes ("T" on the ‘sex’ dimension), expressed as a percentage of active population ("PC_ACT" on the ‘unit’ dimension):

.. ipython:: python

    data.loc[("A", "Y15-74", "PC_ACT", "T")]
