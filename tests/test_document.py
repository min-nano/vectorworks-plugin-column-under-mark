"""命令セットのスキーマ検証 (document.validate_document) のテスト。vs 非依存。"""
from __future__ import annotations

import pytest

from vectorworks_plugin_column_under_mark.document import (
    DOCUMENT_VERSION,
    validate_document,
)


def _valid_document() -> dict:
    return {
        'version': DOCUMENT_VERSION,
        'marks': [
            {'segments': [
                [[-150.0, -150.0], [150.0, 150.0]],
                [[-150.0, 150.0], [150.0, -150.0]],
            ]},
        ],
    }


class TestValidateDocument:
    def test_valid_document_passes(self) -> None:
        result = validate_document(_valid_document())
        assert result['version'] == DOCUMENT_VERSION
        assert len(result['marks']) == 1
        assert len(result['marks'][0]['segments']) == 2

    def test_coordinates_are_coerced_to_float(self) -> None:
        document = {
            'version': DOCUMENT_VERSION,
            'marks': [{'segments': [[[0, 0], [10, 10]]]}],
        }
        result = validate_document(document)
        segment = result['marks'][0]['segments'][0]
        assert segment == [[0.0, 0.0], [10.0, 10.0]]
        assert all(isinstance(v, float) for point in segment for v in point)

    def test_empty_marks_is_valid(self) -> None:
        result = validate_document({'version': DOCUMENT_VERSION, 'marks': []})
        assert result['marks'] == []

    def test_wrong_version_rejected(self) -> None:
        with pytest.raises(ValueError):
            validate_document({'version': DOCUMENT_VERSION + 1, 'marks': []})

    def test_non_dict_rejected(self) -> None:
        with pytest.raises(ValueError):
            validate_document([1, 2, 3])

    def test_marks_not_list_rejected(self) -> None:
        with pytest.raises(ValueError):
            validate_document({'version': DOCUMENT_VERSION, 'marks': 'x'})

    def test_segment_wrong_point_count_rejected(self) -> None:
        document = {
            'version': DOCUMENT_VERSION,
            'marks': [{'segments': [[[0.0, 0.0]]]}],
        }
        with pytest.raises(ValueError):
            validate_document(document)

    def test_non_numeric_coordinate_rejected(self) -> None:
        document = {
            'version': DOCUMENT_VERSION,
            'marks': [{'segments': [[['a', 0.0], [1.0, 1.0]]]}],
        }
        with pytest.raises(ValueError):
            validate_document(document)

    def test_boolean_coordinate_rejected(self) -> None:
        document = {
            'version': DOCUMENT_VERSION,
            'marks': [{'segments': [[[True, 0.0], [1.0, 1.0]]]}],
        }
        with pytest.raises(ValueError):
            validate_document(document)
