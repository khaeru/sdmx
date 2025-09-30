"""SDMX-CSV 1.0 format."""

from dataclasses import dataclass

from sdmx.format.csv.common import CSVFormat, CSVFormatOptions, Labels


class FORMAT(CSVFormat):
    version = "1.0"


@dataclass
class FormatOptions(CSVFormatOptions):
    """Format options for SDMX-CSV version 1.0."""

    format = FORMAT

    def __post_init__(self) -> None:
        if self.labels is Labels.name:
            raise ValueError("Labels.name is not valid for SDMX-CSV 1.0")
