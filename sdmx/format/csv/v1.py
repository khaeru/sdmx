"""SDMX-CSV 1.0 format."""

from dataclasses import dataclass

from sdmx.format.csv.common import CSVFormat, CSVFormatOptions


class FORMAT(CSVFormat):
    version = "1.0"


@dataclass
class FormatOptions(CSVFormatOptions):
    """Format options for SDMX-CSV version 1.0."""

    format = FORMAT
