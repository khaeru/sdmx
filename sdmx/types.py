from typing import TypedDict

from sdmx.convert.pandas import Attributes
from sdmx.format.csv.common import CSVFormatOptions
from sdmx.model.common import Agency


class VersionableArtefactArgs(TypedDict, total=False):
    version: str


class MaintainableArtefactArgs(VersionableArtefactArgs):
    maintainer: Agency


class ToCSVArgs(TypedDict, total=False):
    attributes: Attributes
    format_options: CSVFormatOptions
