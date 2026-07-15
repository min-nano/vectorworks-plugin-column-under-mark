"""指定レイヤ・クラスの柱 (構造用途=柱/小屋束) を検索する。vs 依存。

親プロジェクトの柱・横架材は VectorWorks の構造材ツール
(プラグインオブジェクト ``StructuralMember``) で描かれ、構造用途
(``StructuralUse`` レコードフィールド) が柱="4"・小屋束="5" になる。
このモジュールは指定レイヤ・クラスの構造材のうち構造用途が柱または小屋束の
ものを検索し、その平面位置 (ワールド座標) のリストを返す。
"""
from __future__ import annotations

import vs

from ..core import KIND_COLUMN, KIND_KOYAZUKA, Bounds, ColumnPosition

# 構造材ツールのプラグインオブジェクト名・レコード名
RECORD_NAME = 'StructuralMember'
# 構造用途 (StructuralUse) フィールドと、柱として扱う値
FIELD_STRUCTURAL_USE = 'StructuralUse'
STRUCTURAL_USE_COLUMN = '4'    # 柱 (管柱・通し柱)
STRUCTURAL_USE_KOYAZUKA = '5'  # 小屋束
COLUMN_USES = (STRUCTURAL_USE_COLUMN, STRUCTURAL_USE_KOYAZUKA)

# 構造用途 → 記号の種類。柱=KIND_COLUMN、小屋束=KIND_KOYAZUKA。種類ごとの
# 記号形状 (柱→×・小屋束→○ または /) は記号スタイルに応じて core が選ぶ。
USE_TO_KIND = {
    STRUCTURAL_USE_COLUMN: KIND_COLUMN,
    STRUCTURAL_USE_KOYAZUKA: KIND_KOYAZUKA,
}


def build_criteria(layer: str, class_name: str) -> str:
    """レイヤ・クラスで構造材を絞り込む検索条件式を組み立てる。

    構造用途 (柱/小屋束) は条件式では絞れない (レコードフィールド値) ため、
    ここではプラグインオブジェクト名・レイヤ・クラスだけで絞り、構造用途は
    コールバック側 (``is_target_column``) で判定する。レイヤ・クラスが空文字
    の場合はその条件を付けない (= すべて対象)。
    """
    parts = [f"(PON='{RECORD_NAME}')"]
    if layer:
        parts.append(f"(L='{layer}')")
    if class_name:
        parts.append(f"(C='{class_name}')")
    return ' & '.join(parts)


def column_kind(handle: object) -> str | None:
    """構造材の構造用途を記号の種類に変換する。

    柱="4" → ``KIND_COLUMN``、小屋束="5" → ``KIND_KOYAZUKA``。どちらでもない
    (梁など) 場合は ``None`` を返し、対象外とする。
    """
    use = vs.GetRField(handle, RECORD_NAME, FIELD_STRUCTURAL_USE)
    return USE_TO_KIND.get(use)


def is_target_column(handle: object) -> bool:
    """構造材の構造用途が柱または小屋束かどうかを判定する。"""
    return column_kind(handle) is not None


def section_bounds(handle: object) -> Bounds:
    """構造材の実断面 (平面への投影の外接矩形) をワールド座標で返す。

    ``vs.GetBBox`` は対象の**画面平面への投影**の外接矩形を返す。垂直な柱・
    小屋束では平面への投影がその断面 (伏図での見え掛かり) になるため、これを
    実断面として断面記号の寸法・位置に用いる。戻り値は対角する 2 隅
    ``(x1, y1, x2, y2)``。
    """
    (x1, y1), (x2, y2) = vs.GetBBox(handle)
    return (x1, y1, x2, y2)


def find_column_positions(
    layer: str, class_name: str
) -> list[ColumnPosition]:
    """指定レイヤ・クラスの柱・小屋束の位置情報を返す。

    条件式で構造材を絞り込み、構造用途が柱/小屋束のものだけを採る。各要素は
    ``ColumnPosition`` で、挿入点 (``GetSymLoc``)・記号の種類 (柱→``KIND_COLUMN``
    / 小屋束→``KIND_KOYAZUKA``)・実断面の外接矩形 (``GetBBox``) を持つ。実断面は
    断面記号で寸法・位置を実断面に合わせるために使う。
    """
    positions: list[ColumnPosition] = []

    def collect(handle: object) -> None:
        kind = column_kind(handle)
        if kind is not None:
            x, y = vs.GetSymLoc(handle)
            positions.append(
                ColumnPosition(x, y, kind, section_bounds(handle))
            )

    vs.ForEachObject(collect, build_criteria(layer, class_name))
    return positions
