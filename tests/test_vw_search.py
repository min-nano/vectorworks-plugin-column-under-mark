"""検索フェーズ (vw.search) のテスト。vs をモックして柱検索を検証する。"""
from __future__ import annotations

import importlib
from typing import Any, Callable
from unittest.mock import MagicMock, patch


def _make_vs_mock(objects: dict[str, tuple[str, float, float]]) -> MagicMock:
    """構造材オブジェクトのモック。

    objects: handle -> (structural_use, x, y)。ForEachObject は条件に
    かかわらず全 handle をコールバックに渡し (条件式の絞り込みは VW 側の
    責務)、構造用途による選別はコールバック内の is_target_column が行う。
    """
    vs_mock = MagicMock()

    def for_each_object(callback: Callable[[str], None], criteria: str) -> None:
        for handle in objects:
            callback(handle)

    def get_rfield(handle: str, record: str, field: str) -> str:
        return objects[handle][0]

    def get_sym_loc(handle: str) -> tuple[float, float]:
        return (objects[handle][1], objects[handle][2])

    vs_mock.ForEachObject.side_effect = for_each_object
    vs_mock.GetRField.side_effect = get_rfield
    vs_mock.GetSymLoc.side_effect = get_sym_loc
    return vs_mock


def _load_search(vs_mock: MagicMock) -> Any:
    with patch.dict('sys.modules', {'vs': vs_mock}):
        import vectorworks_plugin_column_under_mark.vw.search as search
        importlib.reload(search)
        return search


class TestFindColumnPositions:
    def test_returns_positions_of_columns_and_koyazuka(self) -> None:
        vs_mock = _make_vs_mock({
            'a': ('4', 1000.0, 2000.0),   # 柱
            'b': ('5', 3000.0, 4000.0),   # 小屋束
        })
        search = _load_search(vs_mock)
        positions = search.find_column_positions('1-柱', '')
        assert positions == [(1000.0, 2000.0), (3000.0, 4000.0)]

    def test_excludes_non_column_structural_use(self) -> None:
        vs_mock = _make_vs_mock({
            'a': ('4', 1000.0, 2000.0),   # 柱 → 採用
            'b': ('1', 5000.0, 6000.0),   # 梁 → 除外
            'c': ('', 7000.0, 8000.0),    # 用途不明 → 除外
        })
        search = _load_search(vs_mock)
        positions = search.find_column_positions('1-柱', '')
        assert positions == [(1000.0, 2000.0)]

    def test_empty_document_yields_no_positions(self) -> None:
        search = _load_search(_make_vs_mock({}))
        assert search.find_column_positions('1-柱', '') == []


class TestBuildCriteria:
    def test_includes_plugin_object_name(self) -> None:
        search = _load_search(_make_vs_mock({}))
        criteria = search.build_criteria('1-柱', '04構造')
        assert "(PON='StructuralMember')" in criteria
        assert "(L='1-柱')" in criteria
        assert "(C='04構造')" in criteria

    def test_omits_empty_layer_and_class(self) -> None:
        search = _load_search(_make_vs_mock({}))
        criteria = search.build_criteria('', '')
        assert criteria == "(PON='StructuralMember')"


class TestIsTargetColumn:
    def test_column_and_koyazuka_are_targets(self) -> None:
        vs_mock = _make_vs_mock({'a': ('4', 0.0, 0.0), 'b': ('5', 0.0, 0.0)})
        search = _load_search(vs_mock)
        assert search.is_target_column('a') is True
        assert search.is_target_column('b') is True

    def test_beam_is_not_target(self) -> None:
        vs_mock = _make_vs_mock({'a': ('1', 0.0, 0.0)})
        search = _load_search(vs_mock)
        assert search.is_target_column('a') is False
