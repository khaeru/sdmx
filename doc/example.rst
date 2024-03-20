Ten-line usage example
======================

Suppose we want to analyze annual unemployment data for some European countries.

All we need to know in advance is the data provider: Eurostat.
:mod:`sdmx` makes it easy to inspect all **data flows** available from this provider. [1]_
The data we want is in a data flow with the identifier ‘UNE_RT_A’.
The description of this data flow references a **data structure definition** (**DSD**) that happens to also have the ID ‘UNE_RT_A’. [2]_

First we create a :class:`.Client` that we will use to make multiple queries to this provider's SDMX-REST web service:

.. ipython:: python

    import sdmx
    estat = sdmx.Client("ESTAT")

Next, we download a **structure message**  containing the DSD and other structural information that it references.
These include *structural metadata* that together completely describe the data available through this dataflow: the concepts, things measured, dimensions, lists of codes used to label each dimension, attributes, and so on:

.. ipython:: python

    sm = estat.datastructure("UNE_RT_A", params=dict(references="descendants"))
    sm

:py:`sm` is a Python object of class :class:`.StructureMessage`.
We can explore some of the specific artifacts—for example, two **code lists**—using :meth:`.StructureMessage.get` to retrieve them and :func:`.to_pandas` to convert to :class:`.pandas.Series`:

.. ipython:: python

    for cl in "AGE", "SEX":
        print(sdmx.to_pandas(sm.get(cl)))

Next, we download a **data set** containing a portion of the data in this data flow, structured by this DSD.
To obtain data only for Greece, Ireland and Spain, we use codes from the code list with the ID ‘GEO’ to specify a **key** for the dimension with the ID ‘geo’. [3]_
We also use a **query parameter**, ‘startPeriod’, to limit the scope of the data returned along the ‘TIME_PERIOD’ dimension.
The query returns a **data message** (Python object of :class:`.DataMessage`) containing the data set:

.. ipython:: python

    dm = estat.data(
        "UNE_RT_A",
        key={"geo": "EL+ES+IE"},
        params={"startPeriod": "2014"},
    )

We again use :func:`.to_pandas` to convert the entire :py:`dm` to a :class:`pandas.Series` with a multi-level index (one level per dimension of the DSD).
Then we can use pandas' built-in methods, like :meth:`pandas.Series.xs` to take a cross-section, selecting on the ‘age’ index level (=SDMX dimension):

.. ipython:: python

    data = (
        sdmx.to_pandas(dm)
        .xs("Y15-74", level="age", drop_level=False)
    )

We further examine the retrieved data set in the familiar form of a :class:`.pandas.Series`.
For one example, show dimension names:

.. ipython:: python

    data.index.names


…and corresponding key values along these dimensions:

.. ipython:: python

    data.index.levels

Select some data of interest: show aggregate unemployment rates across ages ("Y15-74" on the ‘age’ dimension) and sexes ("T" on the ‘sex’ dimension), expressed as a percentage of active population ("PC_ACT" on the ‘unit’ dimension):

.. ipython:: python

    data.loc[("A", "Y15-74", "PC_ACT", "T")]

.. [1] This example skips these steps.
   For a longer explanation, see :ref:`the walkthrough <walkthrough-dataflow>`.
.. [2] The standard does not require that these IDs are the same, but it is a practice used by some data providers.
.. [3] Again, note the difference between the ID of a dimension and the ID of the code list used to enumerate that dimension.
   SDMX IDs are case-sensitive.
