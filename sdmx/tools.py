from collections.abc import Collection
from itertools import product

from sdmx.model import common


def dimensions_to_attributes(
    ds: "common.BaseDataSet", dim_ids: Collection[str]
) -> None:
    """Mutate `ds` and the associated DSD, changing dimensions to attributes."""
    dsd = ds.structured_by
    assert dsd is not None
    attrs = []
    for dim_id in dim_ids:
        attrs.append(dsd.attributes.getdefault(id=dim_id))

    # Mutate observations
    for obs, attr in product(ds.obs, attrs):
        if not obs.dimension:
            continue
        if kv := obs.dimension.values.pop(attr.id, None):
            obs.attached_attribute[attr.id] = common.AttributeValue(
                value=kv.value, value_for=attr
            )

    # Mutate group and series keys
    for coll in ds.group, ds.series:
        for k in list(coll):
            k_new = k.copy()
            for attr in attrs:
                if kv := k_new.values.pop(attr.id, None):
                    k_new.attrib[attr.id] = common.AttributeValue(
                        value=kv.value, value_for=attr
                    )
            # Associate observations with the altered GroupKey/SeriesKey
            if k_new != k:
                coll[k_new] = coll.pop(k)

    # Remove dimensions that have been transferred
    dsd.dimensions.components = list(
        filter(lambda d: d.id not in dim_ids, dsd.dimensions.components)
    )
