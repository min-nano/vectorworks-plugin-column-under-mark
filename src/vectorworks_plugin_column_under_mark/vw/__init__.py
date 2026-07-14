"""フェーズ2: VectorWorks 描画・検索 (vs 依存)。

命令セット (``document.py`` のスキーマ参照) に従って vs モジュールで記号を
描画する。柱の検索 (``search``) もこのパッケージが担う。このパッケージだけが
vs に依存する。
"""
from __future__ import annotations

from typing import Any

from ..document import validate_document
from .draw import execute_marks
from .search import find_column_positions

__all__ = ['execute_document', 'execute_marks', 'find_column_positions']


def execute_document(document: Any) -> dict[str, int]:
    """命令セットを検証し、記号を描画する。

    Returns: {'marks': 描画した記号数}
    """
    validated = validate_document(document)
    return {'marks': execute_marks(validated['marks'])}
