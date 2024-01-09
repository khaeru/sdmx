import pytest

from sdmx import Resource, model
from sdmx.model import v21, v30

CLASSES = [
    # Appearing in .model.common
    "Annotation",
    "AnnotableArtefact",
    "IdentifiableArtefact",
    "NameableArtefact",
    "VersionableArtefact",
    "MaintainableArtefact",
    "ActionType",
    "ConstraintRoleType",
    "FacetValueType",
    "ExtendedFacetValueType",
    "Item",
    "ItemScheme",
    "FacetType",
    "Facet",
    "Representation",
    "Code",
    "Codelist",
    "ISOConceptReference",
    "Concept",
    "ConceptScheme",
    "Component",
    "ComponentList",
    "Category",
    "CategoryScheme",
    "Categorisation",
    "Contact",
    "Organisation",
    "Agency",
    "OrganisationScheme",
    "AgencyScheme",
    "Structure",
    "StructureUsage",
    "DimensionComponent",
    "Dimension",
    "TimeDimension",
    "DimensionDescriptor",
    "GroupDimensionDescriptor",
    "AttributeRelationship",
    "DimensionRelationship",
    "GroupRelationship",
    "DataAttribute",
    "AttributeDescriptor",
    "KeyValue",
    "TimeKeyValue",
    "AttributeValue",
    "Key",
    "GroupKey",
    "SeriesKey",
    "CodingFormat",
    "Level",
    "Hierarchy",
    "HierarchicalCode",
    "ConstraintRole",
    "ConstrainableArtefact",
    "SelectionValue",
    "MemberValue",
    "TimeRangeValue",
    "BeforePeriod",
    "AfterPeriod",
    "StartPeriod",
    "EndPeriod",
    "RangePeriod",
    "CubeRegion",
    "MetadataTargetRegion",
    "DataConsumer",
    "DataProvider",
    "DataConsumerScheme",
    "DataProviderScheme",
    "Datasource",
    "SimpleDatasource",
    "QueryDatasource",
    "RESTDatasource",
    "ProvisionAgreement",
    "CustomType",
    "CustomTypeScheme",
    "NamePersonalisation",
    "NamePersonalisationScheme",
    "Ruleset",
    "RulesetScheme",
    "Transformation",
    "UserDefinedOperator",
    "UserDefinedOperatorScheme",
    "FromVTLSpaceKey",
    "ToVTLSpaceKey",
    "VTLConceptMapping",
    "VTLDataflowMapping",
    "VTLMappingScheme",
    "TransformationScheme",
    # Appearing in model.InternationalString
    "DEFAULT_LOCALE",
    "InternationalString",
    # Classes that are distinct in .model.v21 versus .model.v30
    "SelectionValue",
    "MemberValue",
    "TimeRangeValue",
    "BeforePeriod",
    "AfterPeriod",
    "RangePeriod",
    "DataKey",
    "DataKeySet",
    "Constraint",
    "MemberSelection",
    "MeasureDescriptor",
    "DataStructureDefinition",
    "Observation",
    "StructureSpecificDataSet",
    "MetadataStructureDefinition",
    "TextAttributeValue",
    "XHTMLAttributeValue",
    "MetadataSet",
]

V21_ONLY = [
    "ContentConstraint",
    "PrimaryMeasure",
    "NoSpecifiedRelationship",
    "PrimaryMeasureRelationship",
    "ReportingYearStartDay",
    "MeasureDimension",
    "DataflowDefinition",
    "GenericDataSet",
    "GenericTimeSeriesDataSet",
    "StructureSpecificTimeSeriesDataSet",
    "ReportingCategory",
    "ReportingTaxonomy",
    "TargetObject",
    "DataSetTarget",
    "DimensionDescriptorValuesTarget",
    "IdentifiableObjectTarget",
    "ReportPeriodTarget",
    "MetadataTarget",
    "ReportStructure",
    "MetadataStructureDefinition",
    "MetadataflowDefinition",
    "TargetObjectValue",
    "TargetReportPeriod",
    "TargetIdentifiableObject",
    "TargetObjectKey",
    "ReportedAttribute",
    "EnumeratedAttributeValue",
    "NonEnumeratedAttributeValue",
    "OtherNonEnumeratedAttributeValue",
    "MetadataReport",
    "HierarchicalCodelist",
    "ItemAssociation",
    "CodeMap",
    "ItemSchemeMap",
    "CodelistMap",
    "StructureSet",
]

V30_ONLY = [
    "CodelistExtension",
    "GeoRefCode",
    "GeoGridCode",
    "GeoFeatureSetCode",
    "GeoCodelist",
    "GeographicCodelist",
    "GeoGridCodelist",
    "ValueItem",
    "ValueList",
    "MetadataProvider",
    "MetadataProviderScheme",
    "Measure",
    "Dataflow",  # Instead of DataflowDefinition
    "HierarchyAssociation",
    "DataflowRelationship",
    "MeasureRelationship",
    "ObservationRelationship",
    "DataConstraint",
    "MetadataConstraint",
    "MetadataAttributeDescriptor",
    "IdentifiableObjectSelection",
    "MetadataStructureDefinition",
    "Metadataflow",  # Instead of MetadataflowDefinition
    "MetadataAttributeValue",
    "CodedMetadataAttributeValue",
    "UncodedMetadataAttributeValue",
    "OtherUncodedAttributeValue",
    "TargetIdentifiableObject",
]


@pytest.mark.parametrize("module, extra", [(v21, V21_ONLY), (v30, V30_ONLY)])
def test_complete(module, extra):
    """:mod:`.model.v21` and :mod:`model.v30` each expose a complete set of classes."""
    # Each class is available using module.__getattr__
    for name in CLASSES:
        getattr(module, name)

    assert set(CLASSES + extra) == set(dir(module))


@pytest.mark.parametrize(
    "args, expected",
    [
        pytest.param(
            dict(name="Category", package="codelist"),
            None,
            marks=pytest.mark.xfail(
                raises=ValueError, reason="Package 'codelist' invalid for Category"
            ),
        ),
        # Resource types appearing in StructureMessage
        (dict(name=Resource.agencyscheme), model.AgencyScheme),
        (dict(name=Resource.categorisation), model.Categorisation),
        (dict(name=Resource.categoryscheme), model.CategoryScheme),
        (dict(name=Resource.codelist), model.Codelist),
        (dict(name=Resource.conceptscheme), model.ConceptScheme),
        (dict(name=Resource.contentconstraint), v21.ContentConstraint),
        (dict(name=Resource.dataflow), v21.DataflowDefinition),
        (dict(name=Resource.organisationscheme), model.OrganisationScheme),
        (dict(name=Resource.provisionagreement), v21.ProvisionAgreement),
        pytest.param(
            dict(name=Resource.structure),
            v21.DataStructureDefinition,
            marks=pytest.mark.skip(reason="Ambiguous value, not implemented"),
        ),
    ],
)
def test_get_class(args, expected):
    assert expected is model.v21.get_class(**args)


def test_deprecated_import():
    """Deprecation warning when importing SDMX 2.1-specific class from :mod:`.model`."""
    with pytest.warns(
        DeprecationWarning, match=r"DataStructureDefinition from sdmx\.model"
    ):
        model.DataStructureDefinition

    with pytest.raises(ImportError):
        from sdmx.model import Foo  # noqa: F401


def test_dir():
    """:func:`dir` gives only classes in :mod:`.model.common`."""
    assert "CategoryScheme" in dir(model)
    assert "DataStructureDefinition" not in dir(model)
