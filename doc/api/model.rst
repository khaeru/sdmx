.. _api-model:

.. currentmodule:: sdmx.model

.. module:: sdmx.model

SDMX Information Model
**********************

Quick links to classes common to SDMX 2.1 and 3.0:

:class:`~.common.ActionType`
:class:`~.common.Agency`
:class:`~.common.AgencyScheme`
:class:`~.common.AnnotableArtefact`
:class:`~.common.Annotation`
:class:`~.common.Categorisation`
:class:`~.common.Category`
:class:`~.common.CategoryScheme`
:class:`~.common.Concept`
:class:`~.common.ConceptScheme`
:class:`~.common.ConstraintRoleType`
:class:`~.common.Contact`
:class:`~.common.Facet`
:class:`~.common.FacetType`
:class:`~.common.FacetValueType`
:class:`~.common.IdentifiableArtefact`
:class:`~.common.ISOConceptReference`
:class:`~.internationalstring.InternationalString`
:class:`~.common.Item`
:class:`~.common.ItemScheme`
:class:`~.common.MaintainableArtefact`
:class:`~.common.NameableArtefact`
:class:`~.common.Organisation`
:class:`~.common.OrganisationScheme`
:class:`~.common.Representation`
:class:`~.common.UsageStatus`
:class:`~.common.VersionableArtefact`

Quick links to classes specific to the SDMX 2.1 implementation:

:class:`~.v21.ComponentList`
:class:`~.v21.Code`
:class:`~.v21.Codelist`
:class:`~.v21.ConstrainableArtefact`
:class:`~.v21.DataConsumer`
:class:`~.v21.DataProvider`
:class:`~.v21.DataConsumerScheme`
:class:`~.v21.DataProviderScheme`
:class:`~.v21.ConstraintRole`
:class:`~.v21.ComponentValue`
:class:`~.v21.DataKey`
:class:`~.v21.DataKeySet`
:class:`~.v21.Constraint`
:class:`~.v21.SelectionValue`
:class:`~.v21.MemberValue`
:class:`~.v21.TimeRangeValue`
:class:`~.v21.Period`
:class:`~.v21.RangePeriod`
:class:`~.v21.MemberSelection`
:class:`~.v21.AttachmentConstraint`
:class:`~.v21.DimensionComponent`
:class:`~.v21.Dimension`
:class:`~.v21.CubeRegion`
:class:`~.v21.ContentConstraint`
:class:`~.v21.TimeDimension`
:class:`~.v21.MeasureDimension`
:class:`~.v21.PrimaryMeasure`
:class:`~.v21.MeasureDescriptor`
:class:`~.v21.AttributeRelationship`
:data:`~.v21.NoSpecifiedRelationship`
:data:`~.v21.PrimaryMeasureRelationship`
:class:`~.v21.DimensionRelationship`
:class:`~.v21.GroupRelationship`
:class:`~.v21.DataAttribute`
:class:`~.v21.ReportingYearStartDay`
:class:`~.v21.AttributeDescriptor`
:class:`~.v21.Structure`
:class:`~.v21.StructureUsage`
:class:`~.v21.DimensionDescriptor`
:class:`~.v21.GroupDimensionDescriptor`
:class:`~.v21.DataStructureDefinition`
:class:`~.v21.DataflowDefinition`
:class:`~.v21.KeyValue`
:data:`~.v21.TimeKeyValue`
:class:`~.v21.AttributeValue`
:class:`~.v21.Key`
:class:`~.v21.GroupKey`
:class:`~.v21.SeriesKey`
:class:`~.v21.Observation`
:class:`~.v21.DataSet`
:class:`~.v21.StructureSpecificDataSet`
:class:`~.v21.GenericDataSet`
:class:`~.v21.GenericTimeSeriesDataSet`
:class:`~.v21.StructureSpecificTimeSeriesDataSet`
:data:`~.v21.AllDimensions`
:class:`~.v21.MetadataflowDefinition`
:class:`~.v21.MetadataStructureDefinition`
:class:`~.v21.Datasource`
:class:`~.v21.SimpleDatasource`
:class:`~.v21.QueryDatasource`
:class:`~.v21.RESTDatasource`
:class:`~.v21.ProvisionAgreement`

Common to SDMX 2.1 and 3.0
--------------------------

.. automodule:: sdmx.model.internationalstring
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: sdmx.model.common
   :members:
   :exclude-members: InternationalString
   :undoc-members:
   :show-inheritance:

SDMX 2.1
--------

.. automodule:: sdmx.model.v21
   :members:
   :ignore-module-all:
   :exclude-members: ActionType, Agency, AgencyScheme, AnnotableArtefact, Annotation, Categorisation, Category, CategoryScheme, Concept, ConceptScheme, ConstraintRoleType, Contact, Facet, FacetType, FacetValueType, IdentifiableArtefact, ISOConceptReference, Item, ItemScheme, MaintainableArtefact, NameableArtefact, Organisation, OrganisationScheme, Representation, UsageStatus, VersionableArtefact, KeyValue
   :undoc-members:
   :show-inheritance:

   .. autoclass:: KeyValue
      :members:
      :special-members: __eq__
