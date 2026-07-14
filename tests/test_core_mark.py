"""記号ジオメトリ組み立て (core.mark) のテスト。vs 非依存。"""
from __future__ import annotations

from vectorworks_plugin_column_under_mark.core import mark
from vectorworks_plugin_column_under_mark.core.mark import (
    DEFAULT_MARK_SIZE,
    build_cross_mark,
    build_document,
    build_marks,
)
from vectorworks_plugin_column_under_mark.document import DOCUMENT_VERSION


class TestBuildCrossMark:
    def test_two_diagonal_segments(self) -> None:
        command = build_cross_mark(0.0, 0.0, 200.0)
        assert command['segments'] == [
            [[-100.0, -100.0], [100.0, 100.0]],
            [[-100.0, 100.0], [100.0, -100.0]],
        ]

    def test_centered_on_given_point(self) -> None:
        command = build_cross_mark(1000.0, 500.0, 200.0)
        # 全端点の平均が中心 (1000, 500) になる
        xs = [p[0] for seg in command['segments'] for p in seg]
        ys = [p[1] for seg in command['segments'] for p in seg]
        assert sum(xs) / len(xs) == 1000.0
        assert sum(ys) / len(ys) == 500.0


class TestBuildMarks:
    def test_one_mark_per_position(self) -> None:
        positions = [(0.0, 0.0), (1000.0, 2000.0), (-500.0, 300.0)]
        marks = build_marks(positions, (0.0, 0.0), 200.0)
        assert len(marks) == 3

    def test_positions_translated_to_local_by_origin(self) -> None:
        # 挿入点 (origin) を差し引いたローカル座標で記号を作る
        marks = build_marks([(1200.0, 800.0)], (1000.0, 500.0), 200.0)
        # ローカル中心 = (200, 300)
        segments = marks[0]['segments']
        assert segments == [
            [[100.0, 200.0], [300.0, 400.0]],
            [[100.0, 400.0], [300.0, 200.0]],
        ]

    def test_empty_positions_yield_no_marks(self) -> None:
        assert build_marks([], (0.0, 0.0), 200.0) == []

    def test_non_positive_size_falls_back_to_default(self) -> None:
        marks = build_marks([(0.0, 0.0)], (0.0, 0.0), 0.0)
        half = DEFAULT_MARK_SIZE / 2.0
        assert marks[0]['segments'][0] == [[-half, -half], [half, half]]


class TestBuildDocument:
    def test_has_version_and_marks(self) -> None:
        document = build_document([(0.0, 0.0)], (0.0, 0.0), 200.0)
        assert document['version'] == DOCUMENT_VERSION
        assert len(document['marks']) == 1

    def test_module_reexports_default_size(self) -> None:
        assert mark.DEFAULT_MARK_SIZE == DEFAULT_MARK_SIZE
