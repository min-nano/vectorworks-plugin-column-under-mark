"""フェーズ1相当: 記号ジオメトリの組み立て (vs 非依存)。

柱の検索 (vs 依存) で得たワールド座標から、描画すべき記号の線分を
命令セットとして組み立てる。ここには vs や VectorWorks の知識を持ち込まない。
"""
from __future__ import annotations

from .mark import (
    DEFAULT_MARK_SIZE,
    DEFAULT_MARK_STYLE,
    KIND_COLUMN,
    KIND_KOYAZUKA,
    STYLE_PLAN,
    STYLE_SECTION,
    Bounds,
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

__all__ = [
    'DEFAULT_MARK_SIZE',
    'DEFAULT_MARK_STYLE',
    'KIND_COLUMN',
    'KIND_KOYAZUKA',
    'STYLE_PLAN',
    'STYLE_SECTION',
    'Bounds',
    'ColumnPosition',
    'TopRange',
    'build_circle_mark',
    'build_cross_in_bounds',
    'build_cross_mark',
    'build_diagonal_in_bounds',
    'build_diagonal_mark',
    'build_document',
    'build_mark',
    'build_marks',
    'normalize_style',
    'normalize_top_range',
]
