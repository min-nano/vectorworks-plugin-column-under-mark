"""記号ジオメトリ組み立て (core.mark) のテスト。vs 非依存。"""
from __future__ import annotations

from vectorworks_plugin_column_under_mark.core import mark
from vectorworks_plugin_column_under_mark.core.mark import (
    DEFAULT_MARK_SIZE,
    DEFAULT_MARK_STYLE,
    KIND_COLUMN,
    KIND_KOYAZUKA,
    STYLE_PLAN,
    STYLE_SECTION,
    ColumnPosition,
    TopRange,
    build_circle_mark,
    build_cross_in_bounds,
    build_cross_mark,
    build_diagonal_in_bounds,
    build_diagonal_mark,
    build_document,
    build_mark,
    build_marks,
    normalize_style,
    normalize_top_range,
)
from vectorworks_plugin_column_under_mark.document import DOCUMENT_VERSION


class TestBuildCrossMark:
    def test_two_diagonal_segments(self) -> None:
        command = build_cross_mark(0.0, 0.0, 200.0)
        assert command['segments'] == [
            [[-100.0, -100.0], [100.0, 100.0]],
            [[-100.0, 100.0], [100.0, -100.0]],
        ]

    def test_has_no_circles(self) -> None:
        assert build_cross_mark(0.0, 0.0, 200.0)['circles'] == []

    def test_centered_on_given_point(self) -> None:
        command = build_cross_mark(1000.0, 500.0, 200.0)
        # 全端点の平均が中心 (1000, 500) になる
        xs = [p[0] for seg in command['segments'] for p in seg]
        ys = [p[1] for seg in command['segments'] for p in seg]
        assert sum(xs) / len(xs) == 1000.0
        assert sum(ys) / len(ys) == 500.0


class TestBuildCircleMark:
    def test_single_circle_centered_with_half_radius(self) -> None:
        command = build_circle_mark(1000.0, 500.0, 200.0)
        assert command['segments'] == []
        assert command['circles'] == [{'center': [1000.0, 500.0], 'radius': 100.0}]


class TestBuildDiagonalMark:
    def test_single_diagonal_segment(self) -> None:
        command = build_diagonal_mark(0.0, 0.0, 200.0)
        assert command['segments'] == [
            [[-100.0, -100.0], [100.0, 100.0]],
        ]

    def test_has_no_circles(self) -> None:
        assert build_diagonal_mark(0.0, 0.0, 200.0)['circles'] == []

    def test_centered_on_given_point(self) -> None:
        command = build_diagonal_mark(1000.0, 500.0, 200.0)
        xs = [p[0] for seg in command['segments'] for p in seg]
        ys = [p[1] for seg in command['segments'] for p in seg]
        assert sum(xs) / len(xs) == 1000.0
        assert sum(ys) / len(ys) == 500.0


class TestBuildCrossInBounds:
    def test_two_diagonals_across_rectangle(self) -> None:
        # 実断面 (100, 200)-(400, 600) の 4 隅を結ぶ 2 本の対角線
        command = build_cross_in_bounds(100.0, 200.0, 400.0, 600.0)
        assert command['segments'] == [
            [[100.0, 200.0], [400.0, 600.0]],
            [[100.0, 600.0], [400.0, 200.0]],
        ]
        assert command['circles'] == []


class TestBuildDiagonalInBounds:
    def test_single_diagonal_bottom_left_to_top_right(self) -> None:
        command = build_diagonal_in_bounds(100.0, 200.0, 400.0, 600.0)
        assert command['segments'] == [[[100.0, 200.0], [400.0, 600.0]]]
        assert command['circles'] == []

    def test_normalizes_corner_order_to_bottom_left_top_right(self) -> None:
        # 隅の並びが右上→左下でも / (左下→右上) に揃える
        command = build_diagonal_in_bounds(400.0, 600.0, 100.0, 200.0)
        assert command['segments'] == [[[100.0, 200.0], [400.0, 600.0]]]


class TestNormalizeStyle:
    def test_empty_defaults_to_plan(self) -> None:
        assert normalize_style('') == STYLE_PLAN
        assert DEFAULT_MARK_STYLE == STYLE_PLAN

    def test_unknown_defaults_to_plan(self) -> None:
        assert normalize_style('foo') == STYLE_PLAN

    def test_japanese_section_token(self) -> None:
        assert normalize_style('断面記号') == STYLE_SECTION

    def test_english_section_token_case_insensitive(self) -> None:
        assert normalize_style('Section') == STYLE_SECTION

    def test_surrounding_whitespace_ignored(self) -> None:
        assert normalize_style('  断面  ') == STYLE_SECTION


class TestNormalizeTopRange:
    def test_empty_both_unbounded(self) -> None:
        assert normalize_top_range('', '') == TopRange(None, None)

    def test_parses_numbers(self) -> None:
        assert normalize_top_range('1000', '3000') == TopRange(1000.0, 3000.0)

    def test_only_min(self) -> None:
        assert normalize_top_range('1000', '') == TopRange(1000.0, None)

    def test_only_max(self) -> None:
        assert normalize_top_range('', '3000') == TopRange(None, 3000.0)

    def test_non_numeric_becomes_unbounded(self) -> None:
        assert normalize_top_range('abc', 'x') == TopRange(None, None)

    def test_whitespace_is_unbounded(self) -> None:
        assert normalize_top_range('  ', '3000') == TopRange(None, 3000.0)

    def test_swaps_when_min_greater_than_max(self) -> None:
        # 下限 > 上限は入れ替えて整合させる (入力ミスに寛容)
        assert normalize_top_range('3000', '1000') == TopRange(1000.0, 3000.0)


class TestTopRangeContains:
    def test_unbounded_contains_any(self) -> None:
        assert TopRange().contains(1234.0) is True

    def test_none_top_always_contained(self) -> None:
        # 高さ不明は範囲を課さず表示する
        assert TopRange(1000.0, 2000.0).contains(None) is True

    def test_within_inclusive_bounds(self) -> None:
        r = TopRange(1000.0, 2000.0)
        assert r.contains(1000.0) is True   # 下限は含む
        assert r.contains(2000.0) is True   # 上限は含む
        assert r.contains(1500.0) is True

    def test_below_min_excluded(self) -> None:
        assert TopRange(1000.0, 2000.0).contains(999.0) is False

    def test_above_max_excluded(self) -> None:
        assert TopRange(1000.0, 2000.0).contains(2001.0) is False

    def test_only_min_bound(self) -> None:
        r = TopRange(1000.0, None)
        assert r.contains(5000.0) is True
        assert r.contains(999.0) is False

    def test_only_max_bound(self) -> None:
        r = TopRange(None, 2000.0)
        assert r.contains(-5.0) is True
        assert r.contains(2001.0) is False


class TestBuildMark:
    def test_column_kind_builds_cross(self) -> None:
        command = build_mark(KIND_COLUMN, 0.0, 0.0, 200.0)
        assert len(command['segments']) == 2
        assert command['circles'] == []

    def test_koyazuka_kind_builds_circle(self) -> None:
        command = build_mark(KIND_KOYAZUKA, 0.0, 0.0, 200.0)
        assert command['segments'] == []
        assert len(command['circles']) == 1

    def test_unknown_kind_falls_back_to_cross(self) -> None:
        command = build_mark('mystery', 0.0, 0.0, 200.0)
        assert len(command['segments']) == 2
        assert command['circles'] == []

    def test_section_column_uses_bounds_for_cross(self) -> None:
        # 実断面 (bounds) が渡ると × は実断面の 4 隅に合わせる (指定サイズは無視)
        command = build_mark(
            KIND_COLUMN, 0.0, 0.0, 200.0, STYLE_SECTION,
            (100.0, 200.0, 400.0, 600.0),
        )
        assert command['segments'] == [
            [[100.0, 200.0], [400.0, 600.0]],
            [[100.0, 600.0], [400.0, 200.0]],
        ]
        assert command['circles'] == []

    def test_section_koyazuka_uses_bounds_for_single_diagonal(self) -> None:
        command = build_mark(
            KIND_KOYAZUKA, 0.0, 0.0, 200.0, STYLE_SECTION,
            (100.0, 200.0, 400.0, 600.0),
        )
        assert command['segments'] == [[[100.0, 200.0], [400.0, 600.0]]]
        assert command['circles'] == []

    def test_section_without_bounds_falls_back_to_size_cross(self) -> None:
        # bounds 無しの断面記号の柱は指定サイズの × にフォールバック
        command = build_mark(KIND_COLUMN, 0.0, 0.0, 200.0, STYLE_SECTION)
        assert command['segments'] == [
            [[-100.0, -100.0], [100.0, 100.0]],
            [[-100.0, 100.0], [100.0, -100.0]],
        ]
        assert command['circles'] == []

    def test_section_without_bounds_falls_back_to_size_diagonal(self) -> None:
        # bounds 無しの断面記号の小屋束は指定サイズの / にフォールバック
        command = build_mark(KIND_KOYAZUKA, 0.0, 0.0, 200.0, STYLE_SECTION)
        assert command['segments'] == [[[-100.0, -100.0], [100.0, 100.0]]]
        assert command['circles'] == []

    def test_section_zero_area_bounds_falls_back_to_size(self) -> None:
        # 面積ゼロの bounds は使えないので指定サイズにフォールバック
        command = build_mark(
            KIND_KOYAZUKA, 0.0, 0.0, 200.0, STYLE_SECTION,
            (50.0, 50.0, 50.0, 50.0),
        )
        assert command['segments'] == [[[-100.0, -100.0], [100.0, 100.0]]]

    def test_plan_style_ignores_bounds(self) -> None:
        # 平面記号は bounds を無視して挿入点中心・指定サイズの ○ を描く
        command = build_mark(
            KIND_KOYAZUKA, 0.0, 0.0, 200.0, STYLE_PLAN,
            (100.0, 200.0, 400.0, 600.0),
        )
        assert command['segments'] == []
        assert command['circles'] == [{'center': [0.0, 0.0], 'radius': 100.0}]

    def test_unknown_style_falls_back_to_plan(self) -> None:
        command = build_mark(KIND_KOYAZUKA, 0.0, 0.0, 200.0, 'mystery')
        assert command['segments'] == []
        assert len(command['circles']) == 1


class TestBuildMarks:
    def test_one_mark_per_position(self) -> None:
        positions = [
            ColumnPosition(0.0, 0.0, KIND_COLUMN),
            ColumnPosition(1000.0, 2000.0, KIND_KOYAZUKA),
            ColumnPosition(-500.0, 300.0, KIND_COLUMN),
        ]
        marks = build_marks(positions, (0.0, 0.0), 200.0)
        assert len(marks) == 3

    def test_column_translated_to_local_by_origin(self) -> None:
        # 挿入点 (origin) を差し引いたローカル座標で記号を作る
        marks = build_marks(
            [ColumnPosition(1200.0, 800.0, KIND_COLUMN)], (1000.0, 500.0), 200.0
        )
        # ローカル中心 = (200, 300)
        segments = marks[0]['segments']
        assert segments == [
            [[100.0, 200.0], [300.0, 400.0]],
            [[100.0, 400.0], [300.0, 200.0]],
        ]

    def test_koyazuka_translated_to_local_by_origin(self) -> None:
        marks = build_marks(
            [ColumnPosition(1200.0, 800.0, KIND_KOYAZUKA)], (1000.0, 500.0),
            200.0,
        )
        # ローカル中心 = (200, 300)、半径 = 100
        assert marks[0]['circles'] == [{'center': [200.0, 300.0], 'radius': 100.0}]

    def test_empty_positions_yield_no_marks(self) -> None:
        assert build_marks([], (0.0, 0.0), 200.0) == []

    def test_non_positive_size_falls_back_to_default(self) -> None:
        marks = build_marks(
            [ColumnPosition(0.0, 0.0, KIND_COLUMN)], (0.0, 0.0), 0.0
        )
        half = DEFAULT_MARK_SIZE / 2.0
        assert marks[0]['segments'][0] == [[-half, -half], [half, half]]

    def test_default_style_koyazuka_is_circle(self) -> None:
        marks = build_marks(
            [ColumnPosition(0.0, 0.0, KIND_KOYAZUKA)], (0.0, 0.0), 200.0
        )
        assert len(marks[0]['circles']) == 1
        assert marks[0]['segments'] == []

    def test_section_koyazuka_bounds_translated_to_local(self) -> None:
        # 実断面 (1100,700)-(1300,900)・挿入点 (1000,500)
        # → ローカル外接矩形 (100,200)-(300,400) の / (左下→右上)
        marks = build_marks(
            [ColumnPosition(
                1200.0, 800.0, KIND_KOYAZUKA, (1100.0, 700.0, 1300.0, 900.0),
            )],
            (1000.0, 500.0), 200.0, STYLE_SECTION,
        )
        assert marks[0]['segments'] == [[[100.0, 200.0], [300.0, 400.0]]]
        assert marks[0]['circles'] == []

    def test_section_column_bounds_translated_to_local(self) -> None:
        marks = build_marks(
            [ColumnPosition(
                1200.0, 800.0, KIND_COLUMN, (1100.0, 700.0, 1300.0, 900.0),
            )],
            (1000.0, 500.0), 200.0, STYLE_SECTION,
        )
        # ローカル外接矩形 (100,200)-(300,400) の × (4 隅を結ぶ 2 本)
        assert marks[0]['segments'] == [
            [[100.0, 200.0], [300.0, 400.0]],
            [[100.0, 400.0], [300.0, 200.0]],
        ]

    def test_section_without_bounds_uses_size_at_insertion_point(self) -> None:
        # bounds 無しの断面記号は挿入点中心・指定サイズにフォールバック
        marks = build_marks(
            [ColumnPosition(1200.0, 800.0, KIND_KOYAZUKA)], (1000.0, 500.0),
            200.0, STYLE_SECTION,
        )
        # ローカル中心 = (200, 300)、指定サイズ 200 の /
        assert marks[0]['segments'] == [[[100.0, 200.0], [300.0, 400.0]]]


class TestBuildMarksTopRange:
    # 上端 3000 (範囲内) と 6000 (範囲外) の柱 2 本
    positions = [
        ColumnPosition(0.0, 0.0, KIND_COLUMN, None, 3000.0),
        ColumnPosition(100.0, 0.0, KIND_COLUMN, None, 6000.0),
    ]

    def test_default_range_keeps_all(self) -> None:
        assert len(build_marks(self.positions, (0.0, 0.0), 200.0)) == 2

    def test_filters_out_of_range(self) -> None:
        marks = build_marks(
            self.positions, (0.0, 0.0), 200.0, DEFAULT_MARK_STYLE,
            TopRange(2900.0, 3100.0),
        )
        assert len(marks) == 1

    def test_only_max_bound_filters(self) -> None:
        marks = build_marks(
            self.positions, (0.0, 0.0), 200.0, DEFAULT_MARK_STYLE,
            TopRange(None, 4000.0),
        )
        assert len(marks) == 1

    def test_none_top_is_kept(self) -> None:
        # 上端高さ不明の柱は範囲指定があっても描く
        marks = build_marks(
            [ColumnPosition(0.0, 0.0, KIND_COLUMN, None, None)],
            (0.0, 0.0), 200.0, DEFAULT_MARK_STYLE, TopRange(2900.0, 3100.0),
        )
        assert len(marks) == 1


class TestBuildDocument:
    def test_has_version_and_marks(self) -> None:
        document = build_document(
            [ColumnPosition(0.0, 0.0, KIND_COLUMN)], (0.0, 0.0), 200.0
        )
        assert document['version'] == DOCUMENT_VERSION
        assert len(document['marks']) == 1

    def test_top_range_filters_marks(self) -> None:
        positions = [
            ColumnPosition(0.0, 0.0, KIND_COLUMN, None, 3000.0),
            ColumnPosition(100.0, 0.0, KIND_COLUMN, None, 6000.0),
        ]
        document = build_document(
            positions, (0.0, 0.0), 200.0, DEFAULT_MARK_STYLE,
            TopRange(None, 4000.0),
        )
        assert len(document['marks']) == 1

    def test_module_reexports_default_size(self) -> None:
        assert mark.DEFAULT_MARK_SIZE == DEFAULT_MARK_SIZE
