from typing import TypedDict, Union

from sdmx.convert.pandas import Attributes
from sdmx.format import csv
from sdmx.model.common import Agency


class VersionableArtefactArgs(TypedDict, total=False):
    version: str


class MaintainableArtefactArgs(VersionableArtefactArgs):
    maintainer: Agency


class ToCSVArgs(TypedDict, total=False):
    attributes: Attributes
    format: Union[type["csv.v1.FORMAT"], type["csv.v2.FORMAT"], None]
