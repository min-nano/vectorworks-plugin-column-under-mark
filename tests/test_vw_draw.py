"""描画フェーズ (vw.draw) のテスト。vs をモックして線分描画を検証する。"""
from __future__ import annotations

import importlib
from typing import Any
from unittest.mock import MagicMock, patch

from vectorworks_plugin_column_under_mark.document import MarkCommand


def _cross(x: float, y: float, half: float) -> MarkCommand:
    return {'segments': [
        [[x - half, y - half], [x + half, y + half]],
        [[x - half, y + half], [x + half, y - half]],
    ], 'circles': [], 'symbols': []}


def _circle(x: float, y: float, radius: float) -> MarkCommand:
    return {
        'segments': [],
        'circles': [{'center': [x, y], 'radius': radius}],
        'symbols': [],
    }


def _symbol(name: str, x: float, y: float) -> MarkCommand:
    return {
        'segments': [],
        'circles': [],
        'symbols': [{'name': name, 'point': [x, y]}],
    }


def _load_draw(vs_mock: MagicMock) -> Any:
    with patch.dict('sys.modules', {'vs': vs_mock}):
        import vectorworks_plugin_column_under_mark.vw.draw as draw
        importlib.reload(draw)
        return draw


class TestExecuteMarks:
    def test_returns_drawn_count(self) -> None:
        vs_mock = MagicMock()
        draw = _load_draw(vs_mock)
        count = draw.execute_marks([_cross(0, 0, 100), _cross(500, 500, 100)])
        assert count == 2

    def test_empty_commands_return_zero(self) -> None:
        vs_mock = MagicMock()
        draw = _load_draw(vs_mock)
        assert draw.execute_marks([]) == 0
        vs_mock.MoveTo.assert_not_called()

    def test_draws_each_segment_as_moveto_lineto(self) -> None:
        vs_mock = MagicMock()
        draw = _load_draw(vs_mock)
        draw.execute_marks([_cross(0.0, 0.0, 100.0)])

        move_calls = [c.args for c in vs_mock.MoveTo.call_args_list]
        line_calls = [c.args for c in vs_mock.LineTo.call_args_list]
        # × は 2 線分 = MoveTo/LineTo が 2 回ずつ
        assert move_calls == [(-100.0, -100.0), (-100.0, 100.0)]
        assert line_calls == [(100.0, 100.0), (100.0, -100.0)]

    def test_draws_circle_as_full_arc_by_center(self) -> None:
        vs_mock = MagicMock()
        draw = _load_draw(vs_mock)
        draw.execute_marks([_circle(1000.0, 500.0, 150.0)])

        # ○ は円 1 個 = ArcByCenter を全周 (0→360 度) で 1 回。線分は描かない
        vs_mock.MoveTo.assert_not_called()
        vs_mock.LineTo.assert_not_called()
        vs_mock.ArcByCenter.assert_called_once_with(1000.0, 500.0, 150.0, 0.0, 360.0)

    def test_draws_symbol_at_point(self) -> None:
        vs_mock = MagicMock()
        draw = _load_draw(vs_mock)
        draw.execute_marks([_symbol('柱記号', 1000.0, 500.0)])

        # シンボルは vs.Symbol(name, (x, y), 回転角) を 1 回。線分・円は描かない
        vs_mock.MoveTo.assert_not_called()
        vs_mock.ArcByCenter.assert_not_called()
        vs_mock.Symbol.assert_called_once_with('柱記号', (1000.0, 500.0), 0.0)
