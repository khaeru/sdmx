Implementation notes
********************

:mod:`sdmx.model` implements the SDMX :term:`information model`.
This page gives brief explanations of **how** :mod:`sdmx` **implements the standards**, focusing on additional features, conveniences, errata, and interpretations/naming choices that are not strictly determined by the standards.

Although this page is organized to correspond to the standards, it **does not recapitulate them** (:ref:`as stated <not-the-standard>`)—nor does it set out to teach all their details.
For those purposes, see :doc:`resources`; or the :doc:`walkthrough`, which includes some incidental explanations.

.. _sdmx-version-policy:

SDMX versions 2.0, 2.1, and 3.0
===============================

Multiple versions of the SDMX standards have been published:

- 2.0 in November 2005.
- 2.1 in August 2011; published at the International Standards Organization (ISO) in January 2013; and revised multiple times since.
- 3.0 in October 2022.

For the current package, :mod:`sdmx`:

- SDMX 2.0 is not implemented, and no implementation is currently planned.

  - Some data providers still exist which only offer SDMX-ML 2.0 and/or an SDMX 2.0 REST web service.
    These implementations of SDMX 2.0 can be incomplete, inconsistent, or not fully compliant with the standard.
    This makes it more difficulty and costly to support them.
  - While no SDMX 2.0 implementation is planned, contributions from new developers are possible and welcome.

- SDMX 2.1 is implemented, as described on this page.
- SDMX 3.0 is partly implemented, and a full implementation is planned.
  As of v2.11.0, :mod:`sdmx` implements:

  - The SDMX 3.0 information model (:mod:`.model.v30`) to the same extent as SDMX 2.1.
  - Reading of SDMX-ML 3.0 (:mod:`.reader.xml.v30`).

  Also:

  - :mod:`sdmx` recognizes web services implementing the SDMX 3.0 REST API as distinct from 2.1 versions, and will clearly indicate (e.g. with standard Python :class:`NotImplementedError`) where support is not yet implemented.
  - Writing SDMX-ML 3.0 is not yet supported.
  - Reading and writing SDMX-JSON 2.0 is not yet supported. [1]_

- Support for SDMX 3.0 will be expanded incrementally.
  Follow the :doc:`whatsnew`; :issue:`87`; and other GitHub issues and pull requests for details.
- As of 2023-03-10, none of the :doc:`data sources <sources>` pre-packaged with :mod:`sdmx` are known operate a SDMX 3.0 web service or provide SDMX-{ML,JSON} 3.0 data and metadata.
  Please `open an issue <https://github.com/khaeru/sdmx/issues>`__ on GitHub to report “live” examples and specimens of real-world SDMX 3.0 data and services that can be added.

.. [1] See :ref:`sdmx-json`.

.. _im-base-classes:

Abstract classes and data types
===============================

Many classes inherit from one of the following.
For example, every :class:`.Code` is a ``NameableArtefact``; [2]_ this means it has `name` and `description` attributes. Because every ``NameableArtefact`` is an ``IdentifiableArtefact``, a Code also has `id`, `URI`, and `URN` attributes.

:class:`.AnnotableArtefact`
   - has a list of :attr:`~.AnnotableArtefact.annotations`

:class:`.IdentifiableArtefact`
   - has an :attr:`id <.IdentifiableArtefact.id>`, :attr:`URI <.IdentifiableArtefact.uri>`, and :attr:`URN <.IdentifiableArtefact.urn>`.
   - is “annotable”; this means it *also* has the `annotations` attribute of an AnnotableArtefact.

   The ``id`` uniquely identifies the object against others of the same type in a SDMX message.
   The URI and URN are *globally* unique. See `Wikipedia <https://en.wikipedia.org/wiki/Uniform_Resource_Identifier#URLs_and_URNs>`_ for a discussion of the differences between the two.

:class:`.NameableArtefact`
   - has a :attr:`name <.NameableArtefact.name>` and :attr:`description <.NameableArtefact.description>`, and
   - is identifiable, therefore *also* annotable.

:class:`.VersionableArtefact`
   - has a :attr:`version <.VersionableArtefact.version>` number,
   - may be valid between certain times (:attr:`valid_from <.VersionableArtefact.valid_from>`, :attr:`valid_to <.VersionableArtefact.valid_to>`), and
   - is nameable, identifiable, *and* annotable.

:class:`.MaintainableArtefact`
   - is under the authority of a particular :attr:`maintainer <.MaintainableArtefact.maintainer>`, and
   - is versionable, nameable, identifiable, and annotable.

   In an SDMX message, a maintainable object might not be given in full; only as a reference (with :attr:`is_external_reference <.MaintainableArtefact.is_external_reference>` set to :obj:`True`).
   If so, it might have a :attr:`structure_url <.MaintainableArtefact.structure_url>`, where the maintainer provides more information about the object.

The API reference for :mod:`sdmx.model` shows the parent classes for each class, to describe whether they are versionable, nameable, identifiable, and/or maintainable.

Because SDMX is used worldwide, an :class:`.InternationalString` type is used in the IM—for instance, the `name` of a Nameable object is an InternationalString, with zero or more :attr:`localizations <.InternationalString.localizations>` in different locales.

.. [2] Indirectly, through :class:`Item`.

Items and schemes
=================

:class:`.ItemScheme`, :class:`.Item`
   These abstract classes allow for the creation of flat or hierarchical taxonomies.

   ItemSchemes are maintainable (see above); their  :attr:`~.ItemScheme.items` is a collection of Items.
   See the class documentation for details.


Data
====

:class:`Observation <.BaseObservation>`
   A single data point/datum.

   The value is stored as the :attr:`Observation.value <.BaseObservation.value>` attribute.

:class:`.DataSet`
   A collection of Observations, SeriesKeys, and/or GroupKeys.

   .. note:: **There are no 'Series' or 'Group' classes** in the IM!

     Instead, the *idea* of 'data series' within a DataSet is modeled as:

     - SeriesKeys and GroupKeys are associated with a DataSet.
     - Observations are each associated with one SeriesKey and, optionally, referred to by one or more GroupKeys.

     One can choose to think of a SeriesKey *and* the associated Observations, collectively, as a 'data series'.
     But, in order to avoid confusion with the IM, :mod:`sdmx` does not provide 'Series' or 'Group' objects.

   :mod:`sdmx` provides:

   - the :attr:`.DataSet.series` and :attr:`.DataSet.group` mappings from SeriesKey or GroupKey (respectively) to lists of Observations.
   - :attr:`.DataSet.obs`, which is a list of *all* observations in the DataSet.

   Depending on its structure, a DataSet may be :term:`flat`, :term:`cross-sectional` or :term:`time series`.

:class:`.Key`
   Values (:attr:`.Key.values`) for one or more Dimensions.
   The meaning varies:

   Ordinary Keys, e.g. :attr:`.Observation.dimension`
      The dimension(s) varying at the level of a specific observation.

   :class:`.SeriesKey`
      The dimension(s) shared by all Observations in a conceptual series.

   :class:`.GroupKey`
      The dimension(s) comprising the group.
      These may be a subset of all the dimensions in the DataSet, in which case all matching Observations are considered part of the 'group'—even if they are associated with different SeriesKeys.

      GroupKeys are often used to attach AttributeValues; see below.

:class:`.AttributeValue`
  Value (:attr:`.AttributeValue.value`) for a DataAttribute (:attr:`.AttributeValue.value_for`).

  May be attached to any of: DataSet, SeriesKey, GroupKey, or Observation.
  In the first three cases, the attachment means that the attribute applies to all Observations associated with the object.

Data structures
===============

:class:`.Concept`, :class:`ConceptScheme`
   An abstract idea or general notion, such as 'age' or 'country'.

   Concepts are one kind of Item, and are collected in an ItemScheme subclass called ConceptScheme.

:class:`.Dimension`, :class:`.DataAttribute`
   These are :class:`.Components` of a data structure, linking a Concept (:attr:`~.Component.concept_identity`) to its Representation (:attr:`~.Component.local_representation`); see below.

   A component can be either a DataAttribute that appears as an AttributeValue in data sets; or a Dimension that appears in Keys.

:class:`.Representation`, :class:`.Facet`
   For example: the concept 'country' can be represented as:

   - as a value of a certain type (e.g. 'Canada', a :class:`str`), called a Facet;
   - using a Code from a specific CodeList (e.g. 'CA'); multiple lists of codes are possible (e.g. 'CAN'). See below.

:class:`DataStructureDefinition <.BaseDataStructureDefinition>` (DSD)
   Collects structures used in data sets and data flows.
   These are stored as
   :attr:`~.BaseDataStructureDefinition.dimensions`,
   :attr:`~.BaseDataStructureDefinition.attributes`,
   :attr:`~.BaseDataStructureDefinition.group_dimensions`, and
   :attr:`DataStructureDefinition.measures <.v21.DataStructureDefinition.measures>`.

   For example, :attr:`~.BaseDataStructureDefinition.dimensions` is a :class:`.DimensionDescriptor` object that collects a number of Dimensions in a particular order.
   Data that is "structured by" this DSD must have all the described dimensions.

   See the API documentation for details.

Metadata
========

:class:`.Code`, :class:`.Codelist`
   ...
:class:`.Category`, :class:`.CategoryScheme`, :class:`.Categorization`
   Categories serve to classify or categorise things like dataflows, e.g. by subject matter.

   A :class:`.Categorisation` links the thing to be categorised, e.g., a DataFlowDefinition, to a particular Category.

Constraints
===========

:class:`.v21.Constraint`, :class:`.ContentConstraint`
   Classes that specify a subset of data or metadata to, for example, limit the contents of a data flow.

   A ContentConstraint may have:

   1. Zero or more :class:`.CubeRegion` stored at :attr:`~v21.Constraint.data_content_region`.
   2. Zero or one :class:`.DataKeySet` stored at :attr:`~.v21.Constraint.data_content_keys`.

   Currently, :meth:`.ContentConstraint.to_query_string`, used by :meth:`.Client.get` to validate keys based on a data flow definition, only uses :attr:`~v21.Constraint.data_content_region`, if any.
   :attr:`~v21.Constraint.data_content_keys` are ignored.
   None of the data sources supported by :mod:`sdmx` appears to use this latter form.


.. _formats:

Formats
=======

The IM provides terms and concepts for data and metadata, but does not specify *how that (meta)data is stored or represented*.
The SDMX standards include multiple ways to store data, in the following formats:

SDMX-ML
    Based on eXtensible Markup Language (XML).
    SDMX-ML provides a *complete* specification: it can represent every class and property in the IM.

    Reference: https://sdmx.org/?page_id=5008

    - An SDMX-ML document contains exactly one Message.
      See :mod:`sdmx.message` for the different types of Messages and their component parts.
    - See :mod:`.reader.xml`.

.. _sdmx-json:

SDMX-JSON
    Based on JavaScript Object Notation (JSON).
    The SDMX-JSON *format* is versioned differently from the overall SDMX *standard*: SDMX-JSON 1.0 corresponds to SDMX 2.1, and SDMX-JSON 2.0 corresponds to SDMX 3.0.

    SDMX-JSON 1.0 supports only data and not structures or metadata; SDMX-JSON 2.0 adds support for structure information.

    Reference: https://github.com/sdmx-twg/sdmx-json

    - See :mod:`.reader.json`.

    .. versionadded:: 0.5

       Support for SDMX-JSON.

SDMX-CSV
    Based on Comma-Separated Value (CSV).
    Like SDMX-JSON, the SDMX-CSV format supports only data, not structures or metadata.

    Reference: https://github.com/sdmx-twg/sdmx-csv

    :mod:`sdmx` **does not** currently support SDMX-CSV; see :issue:`34`, :issue:`36`.

:mod:`sdmx`:

- reads all kinds of SDMX-ML and SDMX-JSON messages.
- uses, via `sdmx-test-data <https://github.com/khaeru/sdmx-test-data/>`_, specimens of messages in both data formats.
  These are used by the test suite to check that the code functions as intended, but can also be viewed to understand the data formats.


.. _web-service:

Web services
============

The SDMX standards describe both `RESTful <https://en.wikipedia.org/wiki/Representational_state_transfer>`_ and `SOAP <https://en.wikipedia.org/wiki/SOAP>`_ web service APIs.
See :doc:`resources` for the SDMG Technical Working Group's specification of the REST API.
The Eurostat and ECB help materials provide descriptions and examples of HTTP using URLs, parameters and headers to construct queries.

:mod:`sdmx` supports:

- REST web services, i.e. not SOAP services;
- Data retrieved in SDMX version 2.1 :ref:`formats <formats>`.
  Some existing services offer a parameter to select SDMX 2.1 *or* 2.0 format; :mod:`sdmx` does not support the latter.
  Other services *only* provide SDMX 2.0-formatted data; these cannot be used with :mod:`sdmx` (:ref:`see here <sdmx-version-policy>`).

:class:`.Client` constructs valid URLs and automatically add some parameter and header values.
These can be overridden; see :meth:`.Client.get`.
In some cases, Client will make an additional HTTP request to fetch metadata and validate a query.

:class:`.sdmx.Source` and its subclasses handle idiosyncrasies of the web services operated by different agencies, such as:

- parameters or headers that are not supported, or must take very specific, non-standard values, or
- unusual ways of returning data.

For data sources that support it, :mod:`sdmx` automatically adds the HTTP header ``Accept: application/vnd.sdmx.structurespecificdata+xml;`` when the `dsd` argument is provided to :meth:`.Client.get`.

See :doc:`sources` and the source code for the details for each data source.
