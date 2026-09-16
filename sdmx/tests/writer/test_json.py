import pytest

import sdmx
from sdmx import message
from sdmx.format.json import JSON_v10, JSON_v20, JSON_v21, JSONFormat


@pytest.mark.parametrize(
    "message_class",
    [
        message.DataMessage,
        message.ErrorMessage,
        message.MetadataMessage,
        message.StructureMessage,
    ],
)
@pytest.mark.parametrize(
    "json_format",
    [
        pytest.param(JSON_v10, marks=pytest.mark.xfail(raises=NotImplementedError)),
        JSON_v20,
        JSON_v21,
    ],
)
def test_empty_message(
    header: message.Header, message_class, json_format: JSONFormat
) -> None:
    msg = message_class(header=header)

    result = sdmx.to_json(msg, format=json_format)

    assert '{"meta": {"test": false, "id": "N_A"}}' == result
