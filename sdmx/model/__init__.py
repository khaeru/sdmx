from warnings import warn

from . import v21
from .common import (
    ActionType,
    Agency,
    AgencyScheme,
    AnnotableArtefact,
    Categorisation,
    Category,
    CategoryScheme,
    Concept,
    ConceptScheme,
    ConstraintRoleType,
    Contact,
    IdentifiableArtefact,
    Item,
    ItemScheme,
    MaintainableArtefact,
    Organisation,
    OrganisationScheme,
    Representation,
    UsageStatus,
)
from .internationalstring import InternationalString

__all__ = [
    "ActionType",
    "Agency",
    "AgencyScheme",
    "AnnotableArtefact",
    "Categorisation",
    "Category",
    "CategoryScheme",
    "Concept",
    "ConceptScheme",
    "ConstraintRoleType",
    "Contact",
    "IdentifiableArtefact",
    "InternationalString",
    "Item",
    "ItemScheme",
    "MaintainableArtefact",
    "Organisation",
    "OrganisationScheme",
    "Representation",
    "UsageStatus",
]


def __getattr__(name):
    try:
        result = getattr(v21, name)
    except AttributeError:
        raise
    else:
        # TODO reduce number of warnings emitted
        warn(
            message=" ".join(
                [
                    f"Importing {name} from sdmx.model.",
                    f'Use "from sdmx.model.v21 import {name}" instead.',
                ]
            ),
            category=DeprecationWarning,
            stacklevel=2,
        )
        return result
