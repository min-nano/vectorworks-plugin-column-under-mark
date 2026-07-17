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


def _make_vs_mock(columns: dict[str, tuple[str | float, ...]]) -> MagicMock:
    """柱検索・パラメータ読取・描画を追跡するステートフルなモック。

    columns: handle -> (structural_use, x, y[, top])。top (上端高さ) は任意で、
    省略時は 0.0。
    """
    vs_mock = MagicMock()
    vs_mock.GetCustomObjectInfo.return_value = (True, 'ColumnUnderMark', 'PIO', 'REC', None)
    vs_mock.GetName.return_value = PLUGIN_NAME

    def get_rfield(handle: Any, record: str, field: str) -> str:
        # 構造材の構造用途の読取
        if record == 'StructuralMember' and field == 'StructuralUse':
            return str(columns[handle][0])
        # プラグインオブジェクトのパラメータの読取
        return PARAMS.get(field, '')

    def get_sym_loc(handle: Any) -> tuple[float, float]:
        if handle == 'PIO':
            return ORIGIN
        return (float(columns[handle][1]), float(columns[handle][2]))

    def get_bbox(handle: Any) -> tuple[tuple[float, float], tuple[float, float]]:
        # 構造材の実断面 (100×100) を模す。p1=左上・p2=右下。
        x, y = float(columns[handle][1]), float(columns[handle][2])
        return ((x - 50.0, y + 50.0), (x + 50.0, y - 50.0))

    def get_3d_cntr(handle: Any) -> tuple[tuple[float, float], float]:
        # 中心 Z に上端高さ (top) を入れ、Get3DInfo の height=0 と合わせて
        # top_height() が top をそのまま返すようにする。
        x, y = float(columns[handle][1]), float(columns[handle][2])
        top = float(columns[handle][3]) if len(columns[handle]) > 3 else 0.0
        return ((x, y), top)

    def get_3d_info(handle: Any) -> tuple[float, float, float]:
        return (0.0, 0.0, 0.0)

    def for_each_object(callback: Any, criteria: str) -> None:
        for handle in columns:
            callback(handle)

    vs_mock.GetRField.side_effect = get_rfield
    vs_mock.GetSymLoc.side_effect = get_sym_loc
    vs_mock.GetBBox.side_effect = get_bbox
    vs_mock.Get3DCntr.side_effect = get_3d_cntr
    vs_mock.Get3DInfo.side_effect = get_3d_info
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

    def test_section_style_draws_marks_matching_actual_cross_section(self) -> None:
        # MarkStyle='断面' のとき柱=×・小屋束=/ を実断面 (GetBBox) に合わせて描く
        vs_mock = _make_vs_mock({
            'a': ('4', 1100.0, 2100.0),   # 柱 → × (2 線分)
            'b': ('5', 3100.0, 4100.0),   # 小屋束 → / (1 線分)
        })

        def get_rfield(handle: Any, record: str, field: str) -> str:
            if record == 'StructuralMember' and field == 'StructuralUse':
                return {'a': '4', 'b': '5'}[handle]
            if field == 'MarkSize':
                return '200'
            if field == 'MarkStyle':
                return '断面'
            return ''

        vs_mock.GetRField.side_effect = get_rfield
        with patch.dict('sys.modules', {'vs': vs_mock}):
            _reload_vw_modules()
            import vectorworks_plugin_column_under_mark as pkg
            importlib.reload(pkg)
            pkg.run()

        # 柱の × (2 線分) + 小屋束の / (1 線分) = 3 線分。円は描かない。
        assert vs_mock.MoveTo.call_count == 3
        assert vs_mock.LineTo.call_count == 3
        vs_mock.ArcByCenter.assert_not_called()

        move_calls = [c.args for c in vs_mock.MoveTo.call_args_list]
        line_calls = [c.args for c in vs_mock.LineTo.call_args_list]
        # 柱 a: 実断面 world (1050,2150)-(1150,2050)・挿入点 (100,100)
        # → ローカル外接矩形 (950,2050)-(1050,1950) を結ぶ × の 2 本。
        # 指定サイズ 200 ではなく実断面 (100幅) に一致する。
        assert move_calls[:2] == [(950.0, 2050.0), (950.0, 1950.0)]
        assert line_calls[:2] == [(1050.0, 1950.0), (1050.0, 2050.0)]
        # 小屋束 b: 実断面 world (3050,4150)-(3150,4050)・挿入点 (100,100)
        # → ローカル外接矩形の / (左下→右上) 1 本。
        assert move_calls[2] == (2950.0, 3950.0)
        assert line_calls[2] == (3050.0, 4050.0)

    def test_symbol_places_symbol_instead_of_cross_and_circle(self) -> None:
        # MarkSymbol を指定すると平面記号で柱・小屋束ともにシンボルを配置する
        vs_mock = _make_vs_mock({
            'a': ('4', 1100.0, 2100.0),   # 柱
            'b': ('5', 3100.0, 4100.0),   # 小屋束
        })

        def get_rfield(handle: Any, record: str, field: str) -> str:
            if record == 'StructuralMember' and field == 'StructuralUse':
                return {'a': '4', 'b': '5'}[handle]
            if field == 'MarkSize':
                return '200'
            if field == 'MarkSymbol':
                return '柱記号'
            return ''

        vs_mock.GetRField.side_effect = get_rfield
        with patch.dict('sys.modules', {'vs': vs_mock}):
            _reload_vw_modules()
            import vectorworks_plugin_column_under_mark as pkg
            importlib.reload(pkg)
            pkg.run()

        # × / ○ は描かず、各柱位置にシンボルを 2 個配置する
        vs_mock.MoveTo.assert_not_called()
        vs_mock.ArcByCenter.assert_not_called()
        assert vs_mock.Symbol.call_count == 2
        symbol_calls = [c.args for c in vs_mock.Symbol.call_args_list]
        # 柱 a: (1100,2100) 挿入点 (100,100) → ローカル (1000,2000)
        # 小屋束 b: (3100,4100) → ローカル (3000,4000)
        assert symbol_calls == [
            ('柱記号', (1000.0, 2000.0), 0.0),
            ('柱記号', (3000.0, 4000.0), 0.0),
        ]

    def test_top_height_range_filters_out_of_range_columns(self) -> None:
        # TopHeightMin/Max を指定すると上端が範囲内の柱だけに記号を描く
        vs_mock = _make_vs_mock({
            'a': ('4', 1100.0, 2100.0, 3000.0),   # 上端 3000 → 範囲内 → 描く
            'b': ('4', 5100.0, 6100.0, 6000.0),   # 上端 6000 → 範囲外 → 描かない
        })

        def get_rfield(handle: Any, record: str, field: str) -> str:
            if record == 'StructuralMember' and field == 'StructuralUse':
                return '4'
            if field == 'MarkSize':
                return '200'
            if field == 'TopHeightMin':
                return '2900'
            if field == 'TopHeightMax':
                return '3100'
            return ''

        vs_mock.GetRField.side_effect = get_rfield
        with patch.dict('sys.modules', {'vs': vs_mock}):
            _reload_vw_modules()
            import vectorworks_plugin_column_under_mark as pkg
            importlib.reload(pkg)
            pkg.run()

        # 柱 a (上端 3000) のみ描く → × 1 個 → 2 線分。柱 b は範囲外で描かない。
        assert vs_mock.MoveTo.call_count == 2
        move_calls = [c.args for c in vs_mock.MoveTo.call_args_list]
        # 柱 a: (1100,2100) 挿入点 (100,100) → ローカル中心 (1000,2000)
        assert move_calls[0] == (900.0, 1900.0)

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
