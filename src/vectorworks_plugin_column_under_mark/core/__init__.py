"""フェーズ1相当: 記号ジオメトリの組み立て (vs 非依存)。

柱の検索 (vs 依存) で得たワールド座標から、描画すべき記号の線分を
命令セットとして組み立てる。ここには vs や VectorWorks の知識を持ち込まない。
"""
from __future__ import annotations

from .mark import (
    DEFAULT_MARK_SIZE,
    build_cross_mark,
    build_document,
    build_marks,
)

__all__ = [
    'DEFAULT_MARK_SIZE',
    'build_cross_mark',
    'build_document',
    'build_marks',
]
