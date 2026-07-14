"""run() のエンドツーエンドテスト。

検索フェーズ (vw.search) → 記号組み立て (core) → JSON 命令セット → 描画
フェーズ (vw.draw) のパイプライン全体を vs モックで検証する。
"""
from __future__ import annotations

import importlib
from typing import Any
from unittest.mock import MagicMock, patch

# プラグイン名 (パラメータレコード名) と各パラメータ値
PLUGIN_NAME = '柱下記号'
PARAMS = {'TargetLayer': '1-柱', 'TargetClass': '', 'MarkSize': '200'}
# プラグインオブジェクトの挿入点
ORIGIN = (100.0, 100.0)


def _make_vs_mock(columns: dict[str, tuple[str, float, float]]) -> MagicMock:
    """柱検索・パラメータ読取・描画を追跡するステートフルなモック。

    columns: handle -> (structural_use, x, y)。
    """
    vs_mock = MagicMock()
    vs_mock.GetCustomObjectInfo.return_value = (True, 'ColumnUnderMark', 'PIO', 'REC', None)
    vs_mock.GetName.return_value = PLUGIN_NAME

    def get_rfield(handle: Any, record: str, field: str) -> str:
        # 構造材の構造用途の読取
        if record == 'StructuralMember' and field == 'StructuralUse':
            return columns[handle][0]
        # プラグインオブジェクトのパラメータの読取
        return PARAMS.get(field, '')

    def get_sym_loc(handle: Any) -> tuple[float, float]:
        if handle == 'PIO':
            return ORIGIN
        return (columns[handle][1], columns[handle][2])

    def for_each_object(callback: Any, criteria: str) -> None:
        for handle in columns:
            callback(handle)

    vs_mock.GetRField.side_effect = get_rfield
    vs_mock.GetSymLoc.side_effect = get_sym_loc
    vs_mock.ForEachObject.side_effect = for_each_object
    return vs_mock


def _reload_vw_modules() -> None:
    """vs モックを差し替えた状態で vs 依存モジュール (vw) を再読込する。"""
    import vectorworks_plugin_column_under_mark.vw as vw
    import vectorworks_plugin_column_under_mark.vw.draw as vw_draw
    import vectorworks_plugin_column_under_mark.vw.search as vw_search
    importlib.reload(vw_search)
    importlib.reload(vw_draw)
    importlib.reload(vw)


class TestRun:
    def test_draws_cross_for_column_and_circle_for_koyazuka(self) -> None:
        vs_mock = _make_vs_mock({
            'a': ('4', 1100.0, 2100.0),   # 柱 → ×
            'b': ('5', 3100.0, 4100.0),   # 小屋束 → ○
        })
        with patch.dict('sys.modules', {'vs': vs_mock}):
            _reload_vw_modules()
            import vectorworks_plugin_column_under_mark as pkg
            importlib.reload(pkg)
            pkg.run()

        # 柱 → × 1 個 (2 線分) → MoveTo/LineTo が 2 回ずつ
        assert vs_mock.MoveTo.call_count == 2
        assert vs_mock.LineTo.call_count == 2
        # 小屋束 → ○ 1 個 → ArcByCenter が 1 回
        assert vs_mock.ArcByCenter.call_count == 1

    def test_marks_use_local_coordinates(self) -> None:
        # 柱 (1100, 2100)・挿入点 (100, 100)・サイズ 200 → ローカル中心 (1000, 2000)
        vs_mock = _make_vs_mock({'a': ('4', 1100.0, 2100.0)})
        with patch.dict('sys.modules', {'vs': vs_mock}):
            _reload_vw_modules()
            import vectorworks_plugin_column_under_mark as pkg
            importlib.reload(pkg)
            pkg.run()

        move_calls = [c.args for c in vs_mock.MoveTo.call_args_list]
        line_calls = [c.args for c in vs_mock.LineTo.call_args_list]
        assert move_calls == [(900.0, 1900.0), (900.0, 2100.0)]
        assert line_calls == [(1100.0, 2100.0), (1100.0, 1900.0)]

    def test_koyazuka_circle_uses_local_coordinates(self) -> None:
        # 小屋束 (3100, 4100)・挿入点 (100, 100)・サイズ 200
        # → ローカル中心 (3000, 4000)、半径 100
        vs_mock = _make_vs_mock({'a': ('5', 3100.0, 4100.0)})
        with patch.dict('sys.modules', {'vs': vs_mock}):
            _reload_vw_modules()
            import vectorworks_plugin_column_under_mark as pkg
            importlib.reload(pkg)
            pkg.run()

        vs_mock.MoveTo.assert_not_called()
        vs_mock.ArcByCenter.assert_called_once_with(3000.0, 4000.0, 100.0, 0.0, 360.0)

    def test_excludes_non_column_members(self) -> None:
        vs_mock = _make_vs_mock({
            'a': ('4', 1100.0, 2100.0),   # 柱 → 描く
            'b': ('1', 5100.0, 6100.0),   # 梁 → 描かない
        })
        with patch.dict('sys.modules', {'vs': vs_mock}):
            _reload_vw_modules()
            import vectorworks_plugin_column_under_mark as pkg
            importlib.reload(pkg)
            pkg.run()

        # 柱 1 本のみ → × 1 個 → 2 線分
        assert vs_mock.MoveTo.call_count == 2

    def test_no_columns_draws_nothing(self) -> None:
        vs_mock = _make_vs_mock({})
        with patch.dict('sys.modules', {'vs': vs_mock}):
            _reload_vw_modules()
            import vectorworks_plugin_column_under_mark as pkg
            importlib.reload(pkg)
            pkg.run()

        vs_mock.MoveTo.assert_not_called()

    def test_non_numeric_size_falls_back_to_default(self) -> None:
        from vectorworks_plugin_column_under_mark.core.mark import (
            DEFAULT_MARK_SIZE,
        )

        vs_mock = _make_vs_mock({'a': ('4', 100.0, 100.0)})
        # MarkSize が数値に解釈できない場合は既定サイズを使う

        def get_rfield(handle: Any, record: str, field: str) -> str:
            if record == 'StructuralMember' and field == 'StructuralUse':
                return '4'
            if field == 'MarkSize':
                return 'abc'
            return ''

        vs_mock.GetRField.side_effect = get_rfield
        with patch.dict('sys.modules', {'vs': vs_mock}):
            _reload_vw_modules()
            import vectorworks_plugin_column_under_mark as pkg
            importlib.reload(pkg)
            pkg.run()

        # 柱 (100,100)・挿入点 (100,100) → ローカル中心 (0,0)、既定サイズの ×
        half = DEFAULT_MARK_SIZE / 2.0
        move_calls = [c.args for c in vs_mock.MoveTo.call_args_list]
        assert move_calls[0] == (-half, -half)

    def test_aborts_when_not_a_plugin_object(self) -> None:
        vs_mock = _make_vs_mock({'a': ('4', 1100.0, 2100.0)})
        vs_mock.GetCustomObjectInfo.return_value = (False, '', None, None, None)
        with patch.dict('sys.modules', {'vs': vs_mock}):
            _reload_vw_modules()
            import vectorworks_plugin_column_under_mark as pkg
            importlib.reload(pkg)
            pkg.run()

        vs_mock.ForEachObject.assert_not_called()
        vs_mock.MoveTo.assert_not_called()
