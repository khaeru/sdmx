:tocdepth: 2

What's new?
***********

.. Next release
.. ============

v2.14.0 (2024-02-20)
====================

- Add support for :ref:`SDMX 3.0 REST APIs <sdmx-rest>` (:pull:`158`).
  (Note that SDMX-REST v2.1.0 corresponds to version 3.0 of the overall SDMX standards; see the docs.)

  - Add :class:`.v21.URL` and :class:`.v30.URL` to construct URLs for different API versions.
  - Add :class:`Resource.availableconstraint <.Resource>` and construct (meta)data availability queries per the SDMX 2.1 (REST API v1.5.0) standard (:pull:`161`; thanks :gh-user:`FedorYatsenko`).
  - Add :attr:`.source.Source.versions` attribute to identify REST API versions supported by each source, and :meth:`.Source.get_url_class`.
  - Add :class:`ESTAT3 <.estat3.Source>`, a separate :ref:`ESTAT <ESTAT>` data source that makes SDMX 3.0 (REST API v2.1.0) queries.

- Add four new :ref:`ESTAT <ESTAT>`-related data sources: :ref:`ESTAT_COMEXT` and :ref:`COMP` (:pull:`130`).
- Automatically handle unsupported values of the ``?references=...`` query parameter for the :ref:`COMP` data sources (:issue:`162`, :pull:`163`).
- Bug fix for reading SDMX-ML 2.1: some associations (particularly, :attr:`.core_representation`) not stored correctly if a message contained two :class:`.MaintainableArtefact` with the same ID but different maintainer/version (:pull:`165`, thanks :gh-user:`sychsergiy` for :issue:`164`).
- Drop quirks handling for :ref:`ILO` added in :ref:`v2.6.3` (:pull:`158`).
  The source no longer exhibits the same limitations.

v2.13.1 (2024-01-24)
====================

- Bug fix for reading :class:`.Agency` from SDMX-ML 2.1: name of the parent :class:`.Organisation` would be incorrectly attached to the Contact (:pull:`159`).
- Bug fix for writing :class:`.Contact` to SDMX-ML 2.1: :attr:`.Contact.uri` and :attr:`.Contact.email` would be written as, for instance, :xml:`<str:URI text="https://example.com"/>` instead of :xml:`<str:URI>https://example.com</str:URI>` (:pull:`159`).

v2.13.0 (2024-01-23)
====================

- Expand :mod:`.model` and :mod:`.reader.xml` support for metadata structures and metadata sets (§7 of the Information Model in both SDMX 2.1 and 3.0) (:issue:`73`, :pull:`152`).
  This includes the additional classes:

  - :mod:`.model.common`:
    :class:`.CodingFormat`
    :class:`.ExtendedFacetValueType`
    :class:`.HierarchicalCode`
    :class:`.Level`.
  - :mod:`.model.v21`:
    :class:`.CodelistMap`
    :class:`.CodeMap`
    :class:`.DataSetTarget`
    :class:`.DimensionDescriptorValuesTarget`
    :class:`.EnumeratedAttributeValue`
    :class:`.IdentifiableObjectTarget`
    :class:`.ItemAssociation`
    :class:`.ItemSchemeMap`
    :class:`.MetadataReport`
    :class:`.MetadataSet`
    :class:`.MetadataTarget`
    :class:`.NonEnumeratedAttributeValue`
    :class:`.OtherNonEnumeratedAttributeValue`
    :class:`.ReportedAttribute`
    :class:`.ReportingCategory`
    :class:`.ReportingTaxonomy`
    :class:`.ReportPeriodTarget`
    :class:`.ReportStructure`
    :class:`.StructureSet`
    :class:`.TargetIdentifiableObject`
    :class:`.TargetObject`
    :class:`.TargetObjectKey`
    :class:`.TargetObjectValue`
    :class:`.TargetReportPeriod`
    :class:`.TextAttributeValue`
    :class:`.XHTMLAttributeValue`.
  - :mod:`.model.v30`:
    :class:`.CodedMetadataAttributeValue`
    :class:`.IdentifiableObjectSelection`
    :class:`.MetadataAttributeDescriptor`
    :class:`.MetadataAttributeValue`
    :class:`.Metadataflow`
    :class:`.MetadataSet`
    :class:`.MetadataStructureDefinition`
    :class:`.OtherUncodedAttributeValue`
    :class:`.TargetIdentifiableObject`
    :class:`.TextAttributeValue`
    :class:`.UncodedMetadataAttributeValue`
    :class:`.XHTMLAttributeValue`.
- New collections on StructureMessage:
  :attr:`.hierarchical_codelist`,
  :attr:`.hierarchy`,
  :attr:`.metadatastructure`.
- New class :class:`.MetadataMessage`.
- Improve :class:`.Structure`:

  - New attribute :attr:`~.Structure.grouping` per the information model.
  - New convenience method :meth:`~.Structure.replace_grouping`.
- :mod:`.reader.xml` parses messages available from 'actualconstraint', 'allowedconstraint', 'contentconstraint', 'hierarchicalcodelist', 'metadatstructure', 'structure', and 'structureset' SDMX 2.1 REST API endpoints for all known data sources that support these.

  - Expand explicit marking of particular data sources that do not support the above endpoints.

- Add support for validating SDMX-ML messages; see :func:`.validate_xml` (:issue:`51`; thanks :gh-user:`goatsweater` for :pull:`154`).
- :mod:`sdmx` is fully compatible with pandas 2.2.0, released 2024-01-19 (:pull:`156`).

v2.12.1 (2023-12-20)
====================

- Python 3.12 (released 2023-10-02) is fully supported (:pull:`145`).
- Bugfix: :py:`dsd=...` argument supplied to the SDMX-ML reader ignored in v2.11.0 and later, causing a warning (:pull:`147`; thanks :gh-user:`miccoli` for :issue:`146`).
- Bugfix: attribute :xml:`<str:Attribute assignmentStatus="…">` not read from SDMX-ML (:pull:`150`, thanks :gh-user:`goatsweater` for :issue:`149`).
- Bugfix: items not written by :mod:`.writer.xml` (:pull:`150`, thanks :gh-user:`goatsweater` for :issue:`149`).

  - :attr:`.Annotation.title` → :xml:`<com:AnnotationTitle>…<com:AnnotationTitle/>`.
  - :attr:`.DimensionComponent.order` → :xml:`<str:Dimension position="…">`.
  - :class:`.PrimaryMeasureRelationship` → specific reference to the :attr:`~.IdentifiableArtefact.id` of the :class:`.PrimaryMeasure` within the associated :class:`DataStructureDefinition <.BaseDataStructureDefinition>`.

v2.12.0 (2023-10-11)
====================

- Fix two bugs in parsing :class:`.ItemScheme` from SDMX-ML: :attr:`.VersionableArtefact.valid_from`, :attr:`~.VersionableArtefact.valid_to` not stored, and :class:`Annotations <.Annotation>` for the scheme itself erroneously collected by the first :class:`.Item` in the scheme (:pull:`143`; thanks :gh-user:`goatsweater` for :issue:`142`).
- Update :ref:`OECD <OECD>` to support the provider's recently-added SDMX-ML API (:pull:`140`).
  Rename the corresponding, older SDMX-JSON source :ref:`OECD_JSON <OECD_JSON>`; work around a known issue with its SSL configuration (see :func:`.oecd_json.Client`).

v2.11.0 (2023-08-04)
====================

Migration notes
---------------

- As advertised in :ref:`v2.8-migrate`, user code should import either :mod:`sdmx.model.v21` or :mod:`sdmx.model.v30`.
  When working with data or structures queried from an SDMX 2.1 or 3.0 data source, be sure to use the corresponding information model (IM).
  Mixing classes from the two IMs is not supported and may lead to unexpected behaviour.
- There are several differences between the SDMX 2.1 and 3.0 IMs:
  the new standards delete some classes, change the name or behaviour of others, and add entirely new classes.
  (The `“Standards” page of the SDMX website <https://sdmx.org/?page_id=5008>`_ includes a link to a document with a “Summary of Changes and New Functionalities”.)
  User code that functions against :mod:`.model.v21` **must** be updated if it uses deleted or renamed classes; it **may** need updating if it depends on behaviour that changes in SDMX 3.0.

All changes
-----------

- Implement the SDMX 3.0 Information Model (:mod:`.model.v30`) and a SDMX-ML 3.0 reader (:mod:`.reader.xml.v30`) (:pull:`135`).
- Add :func:`.util.item_structure.parse_item_description`, :func:`.parse_item`, and :func:`.parse_all` for handling common, but non-standard "structure expressions" like "A = B + C - D" in the :attr:`description <.NameableArtefact.description>` of :class:`Items <.Item>` in :class:`ItemSchemes <.ItemScheme>` (or subclasses, e.g. :class:`.Code` in :class:`.Codelist`) (:issue:`133`, :pull:`137`).
  See examples and further description in the function documentation.
- Update the :ref:`ECB` data source URL per a recent change in the service (:pull:`134`).

v2.10.0 (2023-05-20)
====================

- Switch from third-party :py:`pydantic` to Python standard library :mod:`dataclasses` (:pull:`128`).

  This is a major change to the :mod:`sdmx` internals, but should come with few API changes and some performance improvements.
  Specific known changes:

  - Individual classes do not have pydantic-supplied :meth:`copy` methods.
    Use :func:`copy.copy` or :func:`copy.deepcopy` from the standard library, as appropriate.
  - :attr:`.Observation.attached_attribute` values should be set explicitly to :class:`.AttributeValue` instances, rather than to arbitrary types.
    Instead of:

    .. code-block:: python

       from sdmx.model.v21 import Observation

       o = obs()
       o.attached_attribute["CURRENCY"] = "EUR"

    …do:

    .. code-block:: python

       from sdmx.model.v21 import AttributeValue as available

       o.attached_attribute["CURRENCY"] = av("EUR")

- :mod:`.reader.json` properly parses :attr:`.Header.prepared` as a :class:`~datetime.datetime` object from SDMX-JSON data messages (:pull:`128`).
- :mod:`.writer.xml` no longer writes objects in a SDMX-ML :class:`.StructureMessage` if :attr:`.MaintainableArtefact.is_external_reference` is :data:`True` (:pull:`128`).
- Add four new :ref:`ESTAT <ESTAT>`-related data sources: :ref:`ESTAT_COMEXT` and :ref:`COMP` (:pull:`130`).
- Update broken links and other information for some :doc:`sources` (:pull:`130`).
- Update :ref:`ABS` to support the ABS' recently-added “beta” SDMX-ML API (:pull:`129`).
- Rename the corresponding SDMX-JSON source :ref:`ABS_JSON`, update web service URL and quirks handling (:class:`.abs_json.Source`) (:pull:`129`, :pull:`130`).

v2.9.0 (2023-04-30)
===================

- Add :func:`sdmx.to_csv` (:mod:`.writer.csv`) to generate SDMX-CSV 1.0 (corresponding to SDMX 2.1) representation of :class:`DataSets <.DataSet>` (:issue:`36`, :pull:`125`).
- Information Model classes (:pull:`125`):

  - Add :meth:`.AnnotableArtefact.eval_annotation`, which can be used to retrieve Python data structures stored using :func:`repr` as :attr:`.Annotation.text` on an object.
  - Implement :meth:`.KeyValue.__lt__`, for use with Python :func:`.sorted`.
  - Implement :meth:`.DataSet.__str__`.
    The previous default string representation included the representation of *every* observation in the data set, which could be excessively verbose.
    Use ``repr(ds)`` explicitly if this is desired.
  - :meth:`.ComponentList.append` (thus also child classes including :class:`.DimensionDescriptor`) now sets :attr:`.DimensionComponent.order` on the appended components (dimensions), if not already set.
  - Add :meth:`.ComponentList.extend`.

- :mod:`sdmx.writer.xml` (:pull:`125`):

  - Write :attr:`.DataSet.attrib`, i.e. :class:`AttributeValue` attached directly to a data set, rather than to its contents.
  - Write :class:`.Contact`, e.g. within an :class:`.AgencyScheme`.

- Bugfix: correctly handle ``&detail=referencepartial`` REST query parameter and :class:`.StructureMessage` containing ≥2 :class:`.MaintainableArtefact` with the same maintainer and ID, but different versions (:issue:`116`, :pull:`124`).
  See the documentation for :mod:`.reader.xml`.
- :mod:`sdmx` is fully compatible with pandas 2.0.0, released 2023-04-03 (:pull:`124`).
  The minimum version of Python is increased from 3.7 (EOL 2023-06-27) to 3.8.

v2.8.0 (2023-03-31)
===================

.. _v2.8-migrate:

Migration notes
---------------

In order to prepare for future support of SDMX 3.0, code such as the following will emit a :class:`DeprecationWarning`:

.. code-block:: python

   from sdmx.model import DataStructureDefinition
   from sdmx import model

   dsd = model.DataStructureDefinition(...)

This occurs for :mod:`sdmx.model` classes (e.g. :class:`.v21.DataStructureDefinition`) which may have a different implementation in SDMX 3.0 than in SDMX 2.1.
It does *not* occur for classes (e.g. :class:`.InternationalString`) that are unchanged from SDMX 2.1 to 3.0.

Code can be adjusted by importing explicitly from the new :mod:`.model.v21` submodule:

.. code-block:: python

   from sdmx.model.v21 import DataStructureDefinition
   from sdmx.model import v21 as model

   dsd = model.DataStructureDefinition(...)

All changes
-----------

- Outline and prepare for for SDMX 3.0 support (:pull:`120`).
  Read :ref:`sdmx-version-policy` for details.
- The internal :class:`Format` is replaced by a :class:`.MediaType`, allowing to distinguish the “, version=3.0.0” parameters in the HTTP ``Content-Type`` header.
- :attr:`.xml.v21.Reader.media_types` and :attr:`.json.Reader.media_types` explicitly indicate supported media types.
- :attr:`.ItemScheme.is_partial` defaults to :data:`None`.
- Add empty/stub :mod:`.format.csv`, :mod:`.reader.csv` (cf. :issue:`34`), and :mod:`.model.v30`.
- Improve readability in :doc:`implementation` (:pull:`121`).

v2.7.1 (2023-03-09)
===================

- No functional changes.
- Update typing to aid type checking of downstream code (:pull:`117`).
- Update documentation (:pull:`112`) and packaging (:pull:`118`).

v2.7.0 (2022-11-14)
===================

- Python 3.11 is fully supported (:pull:`109`).
- Changes for specific data sources:

  - :ref:`ESTAT`: update web service URL, quirks handling (:class:`.estat.Source`), tests, and usage throughout documentation (:pull:`107`, :pull:`109`, thanks :gh-user:`zymon`).
  - :ref:`IMF`: work around :issue:`102` (thanks :gh-user:`zymon`), an error in some structure messages (:pull:`103`).
  - :ref:`ISTAT`: update web service URL (:pull:`105`; thanks :gh-user:`miccoli` for :issue:`104`).

- Add :class:`~.v21.MetadataflowDefinition`, :class:`~.v21.MetadataStructureDefinition`, and handle references to these in :mod:`.reader.xml` (:pull:`105`).
- Correctly parse "." in item IDs in URNs (:data:`~sdmx.urn.URN`, :pull:`109`).
- Handle SDMX-ML observed in the wild (:pull:`109`):

  - Elements that normally contain text but appear without even a text node, e.g. ``<com:AnnotationURL/>``.
  - XML namespaces defined on the message element, e.g. ``<mes:StructureSpecificData xmlns:u="...">`` followed by ``<u:DataSet>`` instead of ``<mes:DataSet>``.
- Use the user-supplied ``dsd=…`` argument to :meth:`.Client.get`, even if its ID does not match those used locally in an SDMX-ML :class:`.DataMessage` (:pull:`106`, :issue:`104`).
- Expand the :ref:`source/endpoint test matrix <source-matrix>` (:pull:`109`).
  Every REST API endpoint is queried for every data source, even if it is known to be not implemented.
  This allows to spot when source implementations change.
- Sort entries in :file:`sources.json` (:pull:`109`).

.. _v2.6.3:

v2.6.3 (2022-09-29)
===================

- Update :ref:`ILO` web service URL and quirks handling (:pull:`97`, thanks :gh-user:`ethangelbach`).
- Use HTTPS for :ref:`ESTAT` (:pull:`97`).
- Bump minimum version of :py:`pydantic` to 1.9.2 (:pull:`98`).
- Always return all objects parsed from a SDMX-ML :class:`.StructureMessage` (:pull:`99`).

  If two or more :class:`.MaintainableArtefact` have the same ID (e.g. "CL_FOO"); :mod:`sdmx` would formerly store only the last one parsed.
  Now, each is returned, with keys like ``{maintainer's id}:{object id}`` such as would appear in an SDMX URI; for example, "AGENCY_A:CL_FOO", "AGENCY_B:CL_FOO", etc.
- Recognize the MIME type ``application/vnd.sdmx.generic+xml;version=2.1`` (:pull:`99`).
- Catch some cases where :attr:`~.NameableArtefact.name` and :attr:`~.NameableArtefact.description` were discarded when parsing SDMX-ML (:pull:`99`).

v2.6.2 (2022-01-11)
===================

This release contains mainly compatibility updates and testing changes.

- https://khaeru.github.io/sdmx/ now serves a dashboard summarizing automatic, daily tests of every SDMX 2.1 REST API endpoints for every :doc:`data source <sources>` built-in to :mod:`sdmx`.
  See :ref:`source-policy` (:pull:`90`).
- Pydantic >= 1.9 is supported (:pull:`91`).
- Python 3.10 is fully supported (:pull:`89`).

v2.6.1 (2021-07-27)
===================

Bug fixes
---------

- :mod:`.reader.xml` ignored values like ``0`` or ``0.0`` that evaluated equivalent to :obj:`False` (:pull:`86`).

v2.6.0 (2021-07-11)
===================

- Expand documentation of :ref:`source-policy`; add a large number of expected test failures for limitations of specific web services (:pull:`84`).
- Add information from the SDMX-REST standard (:pull:`84`):

  - :data:`.format.FORMATS`, all media (MIME or content) types and their attributes.
  - :class:`.Resource`, expanded and including all resource names appearing in the standard.
  - :data:`.rest.RESPONSE_CODE`.

- Information Model pieces (:pull:`84`):

  - Classes :class:`.DataConsumer` and :class:`.DataProvider`, including reading these from SDMX-ML.
  - Attribute :attr:`.DataSet.described_by`, referencing a :class:`DFD <.DataflowDefinition>` in the same way :attr:`~.DataSet.structured_by` references a :class:`DSD <.v21.DataStructureDefinition>`.

- :mod:`sdmx.writer.xml` (:pull:`84`):

  - Write :class:`.Footer` into messages.
  - Do not create URNs for members of :class:`ItemSchemes <.ItemScheme>`; only write existing URNs.
    This improves round-trip fidelity to original files.

- Convenience methods and functionality (:pull:`84`):

  - :meth:`.StructureMessage.objects` to access collections of structures using a class reference.
  - :func:`len` on :class:`~.v21.MemberSelection`.
  - :func:`.model.get_class` now works with :class:`.Resource` enumeration values as arguments.

- Internal (:pull:`84`):

  - New :class:`.BaseReader` methods :meth:`.supports_content_type` and :meth:`.supports_suffix`.
  - :func:`.util.only`, :func:`.util.parse_content_type`.
  - Improve typing.
  - Expand test coverage.

v2.5.0 (2021-06-27)
===================

- Add :ref:`BBK` and :ref:`BIS` services to supported sources (:pull:`83`).

  - Work around some non-standard behaviours of ``BBK``; see :issue:`82`.

- Document how :ref:`Countdown to 2030 <CD2030>` data can be accessed from the :ref:`UNICEF <UNICEF>` service (:pull:`83`).
- Tolerate malformed SDMX-JSON from :ref:`OECD <OECD>` (:issue:`64`, :pull:`81`).
- Reduce noise when :mod:`requests_cache` is not installed (:issue:`75`, :pull:`80`).
  An exception is still raised if (a) the package is not installed and (b) cache-related arguments are passed to :class:`.Client`.
- Bugfix: `verify` = :obj:`False` was not passed to the preliminary request used to validate a :class:`dict` key for a data request (:pull:`80`; thanks :gh-user:`albertame` for :issue:`77`).
- Handle ``<mes:Department>`` and ``<mes:Role>>`` in SDMX-ML headers (:issue:`78`, :pull:`79`).

v2.4.1 (2021-04-12)
===================

- Fix small bugs in :meth:`.DataStructureDefinition.iter_keys` and related behaviour (:pull:`74`):
  - :meth:`.CubeRegion.__contains__` cannot definitively exclude  :class:`~.v21.KeyValue` when the cube region specifies ≥2 dimensions.
  - :meth:`.MemberSelection.__contains__` is consistent with the sense of :attr:`~.MemberSelection.included`.

v2.4.0 (2021-03-28)
===================

- :class:`.IdentifiableArtefact` can be :func:`.sorted` (:pull:`71`).
- Add :meth:`.DataStructureDefinition.iter_keys` to iterate over valid keys, optionally with a :class:`.v21.Constraint` (:pull:`72`)

  - Also add :meth:`.ContentConstraint.iter_keys`, :meth:`.DataflowDefinition.iter_keys`.
  - Implement or improve :meth:`.Constraint.__contains__`, :meth:`.CubeRegion.__contains__`, :meth:`.ContentConstraint.__contains__`, :meth:`.v21.KeyValue.__eq__`, and :meth:`.Key.__eq__`.

- Speed up creation of :class:`.Key` objects by improving :py:`pydantic` usage, updating :meth:`.Key.__init__`, and adding :meth:`.Key._fast`.
- Simplify :func:`.validate_dictlike`; add :func:`.dictlike_field`, and simplify :py:`pydantic` validation of :class:`.DictLike` objects, keys, and values.

v2.3.0 (2021-03-10)
===================

- :func:`.to_xml` can produce structure-specific SDMX-ML (:pull:`67`).
- Improve typing of :class:`.Item` and subclasses, e.g. :class:`.Code` (:pull:`66`).
  :attr:`~Item.parent` and :attr:`~Item.child` elements are typed the same as a subclass.
- Require :py:`pydantic` >= 1.8.1, and remove workarounds for limitations in earlier versions (:pull:`66`).
- The default branch of the :mod:`sdmx` GitHub repository is renamed ``main``.

Bug fixes
---------

- ``sdmx.__version__`` always gives `999` (:issue:`68`, :pull:`69`).

v2.2.1 (2021-02-27)
===================

- Temporary exclude :py:`pydantic` versions >= 1.8 (:pull:`62`).

v2.2.0 (2021-02-26)
===================

- New convenience method :meth:`.AnnotableArtefact.get_annotation` to return but not remove an Annotation, e.g. by its ID (:pull:`60`).
- Add :file:`py.typed` to support type checking (e.g. with `mypy <https://mypy.readthedocs.io>`_) in packages that depend on :mod:`sdmx`.

v2.1.0 (2021-02-22)
===================

- :meth:`.ItemScheme.append` now raises :class:`ValueError` on duplicate IDs (:pull:`58`).
- :attr:`.Item.parent` stores a reference to the containing :class:`.ItemScheme` for top-level Items that have no hierarchy/parent of their own. This allows navigating from any Item to the ItemScheme that contains it. :meth:`.Item.get_scheme` is added as a convenience method (:pull:`58`).
- :mod:`.reader.xml` internals reworked for significant speedups in parsing of SDMX-ML (:pull:`58`).
- New convenience method :meth:`.StructureMessage.get` to retrieve objects by ID across the multiple collections in StructureMessage (:pull:`58`).
- New convenience method :meth:`.AnnotableArtefact.pop_annotation` to locate, remove, and return a Annotation, e.g. by its ID (:pull:`58`).
- :func:`len` of a :class:`DataKeySet <.BaseDataKeySet>` gives the length of :attr:`.DataKeySet.keys` (:pull:`58`).

v2.0.1 (2021-01-31)
===================

Bug fixes
---------

- :obj:`NoSpecifiedRelationship` and :obj:`PrimaryMeasureRelationship` do not need to be instantiated; they are singletons (:issue:`54`, :pull:`56`).
- `attributes=` "d" ignored in :func:`.to_pandas` (:issue:`55`, :pull:`56`).

v2.0.0 (2021-01-26)
===================

Migration notes
---------------

Code that calls :func:`Request` emits :class:`DeprecationWarning` and logs a message with level :py:data:`~.logging.WARNING`:

.. code-block:: ipython

   >>> sdmx.Request("ECB")
   Request class will be removed in v3.0; use Client(...)
   <sdmx.client.Client object at 0x7f98787e7d60>

Instead, use:

.. code-block:: python

   sdmx.Client("ECB")

Per `the standard semantic versioning approach <https://semver.org/#how-should-i-handle-deprecating-functionality>`_, this feature is marked as deprecated in version 2.0, and will be removed no sooner than version 3.0.

References to ``sdmx.logger`` should be updated to ``sdmx.log``.
Instead of passing the `log_level` parameter to :class:`.Client`, access this standard Python :py:class:`~.logging.Logger` and change its level, as described at :ref:`HOWTO control logging <howto-logging>`.

All changes
-----------

- The large library of test specimens for :mod:`sdmx` is no longer shipped with the package, reducing the archive size by about 80% (:issue:`18`, :pull:`52`).
  The specimens can be retrieved for running tests locally; see :ref:`testing`.
- The :py:`Request` class is renamed :class:`.Client` for semantic clarity (:issue:`11`, :pull:`44`):

  A Client can open a :class:`.requests.Session` and might make many :class:`requests.Requests <.requests.Request>` against the same web service.

- The `log_level` parameter to :class:`.Client` is deprecated.
- Some internal modules are renamed.
  These should not affect user code; if they do, adjust that code to use the top-level objects.

  - :py:`sdmx.api` is renamed :mod:`sdmx.client`.
  - :py:`sdmx.remote` is renamed :mod:`sdmx.session`.
  - :py:`sdmx.reader.sdmxml` is renamed :mod:`sdmx.reader.xml`, to conform with :mod:`sdmx.format.xml` and :mod:`sdmx.writer.xml`.
  - :py:`sdmx.reader.sdmxjson` is renamed :mod:`sdmx.reader.json`.

v1.7 and earlier
================

v1.7.0 (2021-01-26)
-------------------

New features
~~~~~~~~~~~~

- Add :ref:`The Pacific Community's Pacific Data Hub <SPC>` as a data source (:pull:`30`).
- Add classes to :mod:`sdmx.model`: :class:`.v21.TimeRangeValue`, :class:`.Period`, :class:`RangePeriod`, and parse ``<com:TimeRange>`` and related tags in SDMX-ML (:pull:`30`).

Bug fixes
~~~~~~~~~

- Output SDMX-ML header elements in order expected by standard XSD (:issue:`42`, :pull:`43`).
- Respect `override` argument to :func:`.add_source` (:pull:`41`).

v1.6.0 (2020-12-16)
-------------------

New features
~~~~~~~~~~~~

- Support Python 3.9 (using pydantic ≥ 1.7) (:pull:`37`).
- Add :ref:`National Bank of Belgium <NBB>` as a data source (:pull:`32`).
- Add :ref:`Statistics Lithuania <LSD>` as a data source (:pull:`33`).

Bug fixes
~~~~~~~~~

- Data set-level attributes were not collected by :class:`.sdmxml.Reader` (:issue:`29`, :pull:`33`).
- Respect `HTTP[S]_PROXY` environment variables (:issue:`26`, :pull:`27`).

v1.5.0 (2020-11-12)
-------------------

- Add a :doc:`brief tutorial <howto/create>` on creating SDMX-ML messages from pure Python objects (:issue:`23`, :pull:`24`).
- Add :ref:`Statistics Estonia <STAT_EE>` as a data source (:pull:`25`).
- Supply provider=“ALL” to :ref:`INSEE <INSEE>` structure queries by default (:issue:`21`, :pull:`22`)

v1.4.0 (2020-08-17)
-------------------

New features
~~~~~~~~~~~~

- Add :ref:`UNICEF <UNICEF>` service to supported sources (:pull:`15`).
- Enhance :func:`.to_xml` to handle :class:`DataMessages <.DataMessage>` (:pull:`13`).

  In v1.4.0, this feature supports a subset of DataMessages and DataSets.
  If you have an example of a DataMessages that :mod:`sdmx` 1.4.0 cannot write, please `file an issue on GitHub <https://github.com/khaeru/sdmx/issues/new>`_ with a file attachment.
  SDMX-ML features used in such examples will be prioritized for future improvements.

- Add ``compare()`` methods to :class:`.DataMessage`, :class:`.DataSet`, and related classes  (:pull:`13`).

Bug fixes
~~~~~~~~~

- Fix parsing of :class:`.MeasureDimension` returned by :ref:`SGR <SGR>` for data structure queries (:pull:`14`).

v1.3.0 (2020-08-02)
-------------------

- Adjust imports for compatibility with pandas 1.1.0 (:pull:`10`).
- Add :ref:`World Bank World Development Indicators (WDI) <WB_WDI>` service to supported sources (:pull:`10`).

v1.2.0 (2020-06-04)
-------------------

New features
~~~~~~~~~~~~

- Methods like :meth:`.IdentifiableArtefact.compare` are added for recursive comparison of :mod:`.model` objects (:pull:`6`).
- :func:`.to_xml` covers a larger subset of SDMX-ML, including almost all contents of a :class:`.StructureMessage` (:pull:`6`).

v1.1.0 (2020-05-18)
-------------------

Data model changes
~~~~~~~~~~~~~~~~~~

…to bring :mod:`sdmx` into closer alignment with the standard Information Model (:pull:`4`):

- Change :attr:`.Header.receiver` and :attr:`.Header.sender` to optional :class:`.Agency`, not :class:`str`.
- Add :attr:`.Header.source` and :attr:`~.Header.test`.
- :attr:`.IdentifiableArtefact.id` is strictly typed as :class:`str`, with a singleton object (analogous to :obj:`None`) used for missing IDs.
- :attr:`.IdentifiableArtefact.id`, :attr:`.VersionableArtefact.version`, and :attr:`.MaintainableArtefact.maintainer` are inferred from a URN if one is passed during construction.
- :meth:`.VersionableArtefact.identical` and :meth:`.MaintainableArtefact.identical` compare on version and maintainer attributes, respectively.
- :class:`.Facet`, :class:`.Representation`, and :class:`.ISOConceptReference` are strictly validated, i.e. cannot be assigned non-IM attributes.
- Add :class:`.OrganisationScheme`, :class:`.NoSpecifiedRelationship`, :class:`.PrimaryMeasureRelationship`, :class:`.DimensionRelationship`, and :class:`.GroupRelationship` as distinct classes.
- Type of :attr:`.DimensionRelationship.dimensions` is :class:`.DimensionComponent`, not the narrower :class:`.Dimension`.
- :attr:`.v21.DataStructureDefinition.measures` is an empty :class:`.v21.MeasureDescriptor` by default, not :obj:`None`.
- :meth:`.DataSet.add_obs` now accepts :class:`Observations <.v21.Observation>` with no :class:`.SeriesKey` association, and sets this association to the one provided as an argument.
- String representations are simplified but contain more information.

New features
~~~~~~~~~~~~

- :attr:`.Item.hierarchical_id` and :meth:`.ItemScheme.get_hierarchical` create and search on IDs like ‘A.B.C’ for Item ‘A’ with child/grandchild Items ‘B’ and ‘C’ (:pull:`4`).
- New methods :func:`.parent_class`, :func:`.get_reader_for_path`, :func:`.detect_content_reader`, and :func:`.reader.register` (:pull:`4`).
- :class:`.sdmxml.Reader <.xml.v21.Reader>` uses an event-driven, rather than recursive/tree iterating, parser (:pull:`4`).
- The codebase is improved to pass static type checking with `mypy <https://mypy.readthedocs.io>`_ (:pull:`4`).
- Add :func:`.to_xml` to generate SDMX-ML for a subset of the IM (:pull:`3`).

Test suite
~~~~~~~~~~

- :pull:`2`: Add tests of data queries for source(s): OECD


v1.0.0 (2020-05-01)
-------------------

- Project forked and renamed to :mod:`sdmx` (module) / ``sdmx1`` (on PyPI, due to an older, unmaintained package with the same name).
- :mod:`sdmx.model` is reimplemented.

  - Python typing_ and pydantic_ are used to force tight compliance with the SDMX Information Model (IM).
    Users familiar with the IM can use :mod:`sdmx` without the need to understand implementation-specific details.
  - IM classes are no longer tied to :mod:`sdmx.reader` instances and can be created and manipulated outside of a read operation.

- :py:`sdmx.api` and :py:`sdmx.remote` are reimplemented to (1) match the semantics of the requests_ package and (2) be much thinner.
- Data sources are modularized in :class:`~.source.Source`.

  - Idiosyncrasies of particular data sources (e.g. ESTAT's process for large requests) are handled by source-specific subclasses.
    As a result, :py:`sdmx.api` is leaner.

- Testing coverage is significantly expanded.

  - Promised, but untested, features of the 0.x series now have tests, to ensure feature parity.
  - There are tests for each data source (:file:`tests/test_sources.py``) to ensure the package can handle idiosyncratic behaviour.
  - The pytest-remotedata_ pytest plugin allows developers and users to run or skip network tests with `--remote-data`.

.. _typing: https://docs.python.org/3/library/typing.html
.. _pydantic: https://pydantic-docs.helpmanual.io
.. _requests: http://docs.python-requests.org
.. _pytest-remotedata: https://github.com/astropy/pytest-remotedata

Breaking changes
~~~~~~~~~~~~~~~~

- Python 3.6 and earlier (including Python 2) are not supported.

Migrating
~~~~~~~~~

- ``Writer.write(…, reverse_obs=True)``: use the standard pandas indexing approach to reverse a pd.Series: ``s.iloc[::-1]``
- odo support is no longer built-in; however, users can still register a SDMX resource with odo.
  See the :ref:`HOWTO <howto-convert>`.
- :func:`.write_dataset`: the `parse_time` and `fromfreq` arguments are replaced by `datetime`; see the method documentation and the :ref:`walkthrough section <datetime>` for examples.

pandaSDMX (versions 0.9 and earlier)
====================================

pandaSDMX v0.9 (2018-04)
------------------------

This version is the last tested on Python 2.x.
Future versions will be tested on Python 3.5+ only

New features
~~~~~~~~~~~~

* four new data providers INEGI (Mexico), Norges Bank (Norway), International Labour Organization (ILO) and Italian statistics office (ISTAT)
* model: make Ref instances callable for resolving them, i.e. getting the referenced object by making a remote request if needed
* improve loading of structure-specific messages when DSD is not passed / must be requested on the fly
* process multiple and cascading content constraints as described in the Technical Guide (Chap. 6 of the SDMX 2.1 standard)
* StructureMessages and DataMessages now have properties to compute the constrained and unconstrained codelists as dicts of frozensets of codes.
  For DataMessage this is useful when ``series_keys`` was set to True when making the request.
  This prompts the data provider to generate a dataset without data, but with the complete set of series keys.
  This is the most accurate representation of the available series.
  Agencies such as IMF and ECB support this feature.

v0.8.2 (2017-12-21)
-------------------

* fix reading of structure-specific data sets when DSD_ID is present in the data set

v0.8.1 (2017-12-20)
-------------------

* fix broken  package preventing pip installs of the wheel


v0.8 (2017-12-12)
-----------------

* add support for an alternative data set format defined for SDMXML messages.
  These so-called structure-specific data sets lend themselves for large data queries.
  File sizes are typically about 60 % smaller than with equivalent generic data sets.
  To make use of structure-specific data sets, instantiate Request objects with agency IDs such as 'ECB_S', 'INSEE_S' or 'ESTAT_S' instead of 'ECB' etc.
  These alternative agency profiles prompt pandaSDMX to execute data queries for structure-specific data sets.
  For all other queries they behave exactly as their siblings.
  See a code example in chapter 5 of the docs.
* raise ValueError when user attempts to request a resource other than data from an agency delivering data in SCMX-JSON format only (OECD and ABS).
* Update INSEE profile
* handle empty series properly
* data2pd writer: the code for Series index generation was rewritten from scratch to make better use of pandas' time series functionality.
  However, some data sets, in particular from INSEE, which come with bimonthly or semestrial frequencies cannot be rendered as PeriodIndex.
  Pass ``parse_time=False`` to the .write method to prevent errors.


v0.7.0 (2017-06-10)
-------------------

* add new data providers:

  - Australian Bureau of Statistics
  - International Monetary Fund - SDMXCentral only
  - United Nations Division of Statistics
  - UNESCO (free registration required)
  - World Bank - World Integrated Trade Solution (WITS)

* new feature: load metadata on data providers from json file; allow the user to add new agencies on the fly by specifying an appropriate JSON file using the :py:`pandasdmx.api.Request.load_agency_profile`.
* new :meth:`pandasdmx.api.Request.preview_data <.Client.preview_data>` providing a powerful fine-grain key validation algorithm by downloading all series-keys of a dataset and exposing them as a pandas DataFrame which is then mapped to the cartesian product of the given dimension values.
  Works only with data providers such as ECB and UNSD which support "series-keys-only" requests.
  This feature could be wrapped by a browser-based UI for building queries.
* SDMX-JSON reader: add support for flat and cross-sectional datasets, preserve dimension order where possible
* structure2pd writer: in codelists, output Concept rather than Code attributes in the first line of each code-list.
  This may provide more information.

v0.6.1 (2017-02-03)
-------------------

* fix 2to3 issue which caused crashes on Python 2.7


v0.6 (2017-01-07)
-----------------

This release contains some important stability improvements.

Bug fixes
~~~~~~~~~

* JSON data from OECD is now properly downloaded
* The data writer tries to glean a frequency value for a time series from its attributes.
  This is helpful when exporting data sets, e.g., from INSEE (`Issue 41 <https://github.com/dr-leo/pandaSDMX/issues/41>`_).

Known issues
~~~~~~~~~~~~

A data set which lacks a FREQ dimension or attribute can be exported as pandas DataFrame only when `parse_time=False?`, i.e. no DateTime index is generated.
The resulting DataFrame has a string index.
Use pandas magic to create a DateTimeIndex from there.

v0.5 (2016-10-30)
-----------------

New features
~~~~~~~~~~~~

* new reader module for SDMX JSON data messages
* add OECD as data provider (data messages only)
* :class:`pandasdmx.model.Category <.Category>` is now an iterator over categorised objects.
  This greatly simplifies category usage.
  Besides, categories with the same ID while belonging to multiple category schemes are no longer conflated.

API changes
~~~~~~~~~~~

* Request constructor: make agency ID case-insensitive
* As :class:`.Category` is now an iterator over categorised objects, :py:`Categorisations` is no longer considered part of the public API.

Bug fixes
~~~~~~~~~

* SDMX-ML reader: fix AttributeError in write_source method, thanks to Topas
* correctly distinguish between categories with same ID while belonging to different category schemes

v0.4 (2016-04-11)
-----------------

New features
~~~~~~~~~~~~

* add new provider INSEE, the French statistics office (thanks to Stéphan Rault)
* register '.sdmx' files with `Odo <odo.readthedocs.io/>`_ if available
* logging of http requests and file operations.
* new structure2pd writer to export codelists, dataflow-definitions and other structural metadata from structure messages as multi-indexed pandas DataFrames.
  Desired attributes can be specified and are represented by columns.

API changes
~~~~~~~~~~~

* :py:`pandasdmx.api.Request` constructor accepts a ``log_level`` keyword argument which can be set to a log-level for the pandasdmx logger and its children (currently only pandasdmx.api)
* :py:`pandasdmx.api.Request` now has a ``timeout`` property to set the timeout for http requests
* extend api.Request._agencies configuration to specify agency- and resource-specific settings such as headers.
  Future versions may exploit this to provide reader selection information.
* api.Request.get: specify http_headers per request. Defaults are set according to agency configuration
* Response instances expose Message attributes to make application code more succinct
* rename :class:`pandasdmx.api.Message <.Message>` attributes to singular form.
  Old names are deprecated and will be removed in the future.
* :py:`pandasdmx.api.Request` exposes resource names such as data, datastructure, dataflow etc. as descriptors calling 'get' without specifying the resource type as string.
  In interactive environments, this saves typing and enables code completion.
* data2pd writer: return attributes as namedtuples rather than dict
* use patched version of namedtuple that accepts non-identifier strings as field names and makes all fields accessible through dict syntax.
* remove GenericDataSet and GenericDataMessage. Use DataSet and DataMessage instead
* sdmxml reader: return strings or unicode strings instead of LXML smart strings
* sdmxml reader: remove most of the specialized read methods.
  Adapt model to use generalized methods. This makes code more maintainable.
* :class:`sdmx.model.Representation <.Representation>` for DSD attributes and dimensions now supports text not just code lists.

Other changes and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* documentation has been overhauled.
  Code examples are now much simpler thanks to the new structure2pd writer
* testing: switch from nose to py.test
* improve packaging. Include tests in sdist only
* numerous bug fixes

v0.3.1 (2015-10-04)
-------------------

This release fixes a few bugs which caused crashes in some situations.

v0.3.0 (2015-09-22)
-------------------

* support for `requests-cache <https://readthedocs.io/projects/requests-cache/>`_ allowing to cache SDMX messages in memory, MongoDB, Redis or SQLite.
* pythonic selection of series when requesting a dataset: Request.get allows the ``key`` keyword argument in a data request to be a dict mapping dimension names to values.
  In this case, the dataflow definition and datastructure definition, and content-constraint are downloaded on the fly, cached in memory and used to validate the keys.
  The dotted key string needed to construct the URL will be generated automatically.
* The Response.write method takes a ``parse_time`` keyword arg. Set it to False to avoid parsing of dates, times and time periods as exotic formats may cause crashes.
* The Request.get method takes a ``memcache`` keyword argument.
  If set to a string, the received Response instance will be stored in the dict ``Request.cache`` for later use.
  This is useful when, e.g., a DSD is needed multiple times to validate keys.
* fixed base URL for Eurostat
* major refactorings to enhance code maintainability

v0.2.2
------

* Make HTTP connections configurable by exposing the `requests.get API <http://www.python-requests.org/en/latest/>`_ through the :py:`pandasdmx.api.Request` constructor.
  Hence, proxy servers, authorisation information and other HTTP-related parameters consumed by ``requests.get`` can be specified for each ``Request`` instance and used in subsequent requests.
  The configuration is exposed as a dict through a new ``Request.client.config`` attribute.
* Responses have a new ``http_headers`` attribute containing the HTTP headers returned by the SDMX server

v0.2.1
------

* Request.get: allow `fromfile` to be a file-like object
* extract SDMX messages from zip archives if given.
  Important for large datasets from Eurostat
* automatically get a resource at an URL given in the footer of the received message.
  This allows to automatically get large datasets from Eurostat that have been made available at the given URL.
  The number of attempts and the time to wait before each request are configurable via the ``get_footer_url`` argument.


v0.2.0 (2015-04-13)
-------------------

This version is a quantum leap.
The whole project has been redesigned and rewritten from scratch to provide robust support for many SDMX features.
The new architecture is centered around a pythonic representation of the SDMX information model.
It is extensible through readers and writers for alternative input and output formats.
Export to pandas has been dramatically improved.
Sphinx documentation has been added.

v0.1.2 (2014-09-17)
-------------------

* fix xml encoding. This brings dramatic speedups when downloading and parsing data
* extend description.rst


v0.1 (2014-09)
--------------

* Initial release
