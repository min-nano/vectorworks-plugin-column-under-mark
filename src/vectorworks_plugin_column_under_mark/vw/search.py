"""指定レイヤ・クラスの柱 (構造用途=柱/小屋束) を検索する。vs 依存。

親プロジェクトの柱・横架材は VectorWorks の構造材ツール
(プラグインオブジェクト ``StructuralMember``) で描かれ、構造用途
(``StructuralUse`` レコードフィールド) が柱="4"・小屋束="5" になる。
このモジュールは指定レイヤ・クラスの構造材のうち構造用途が柱または小屋束の
ものを検索し、その平面位置 (ワールド座標) のリストを返す。
"""
from __future__ import annotations

import vs

# 構造材ツールのプラグインオブジェクト名・レコード名
RECORD_NAME = 'StructuralMember'
# 構造用途 (StructuralUse) フィールドと、柱として扱う値
FIELD_STRUCTURAL_USE = 'StructuralUse'
STRUCTURAL_USE_COLUMN = '4'    # 柱 (管柱・通し柱)
STRUCTURAL_USE_KOYAZUKA = '5'  # 小屋束
COLUMN_USES = (STRUCTURAL_USE_COLUMN, STRUCTURAL_USE_KOYAZUKA)


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


def is_target_column(handle: object) -> bool:
    """構造材の構造用途が柱または小屋束かどうかを判定する。"""
    use = vs.GetRField(handle, RECORD_NAME, FIELD_STRUCTURAL_USE)
    return use in COLUMN_USES


def find_column_positions(
    layer: str, class_name: str
) -> list[tuple[float, float]]:
    """指定レイヤ・クラスの柱・小屋束の平面位置 (ワールド座標) を返す。

    条件式で構造材を絞り込み、構造用途が柱/小屋束のものだけを採る。位置は
    構造材 (プラグインオブジェクト) の挿入点 (``GetSymLoc``) を用いる。
    """
    positions: list[tuple[float, float]] = []

    def collect(handle: object) -> None:
        if is_target_column(handle):
            x, y = vs.GetSymLoc(handle)
            positions.append((x, y))

    vs.ForEachObject(collect, build_criteria(layer, class_name))
    return positions
