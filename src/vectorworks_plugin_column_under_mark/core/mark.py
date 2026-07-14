"""柱の位置から記号 (× 等) のジオメトリを組み立てる。vs 非依存で単体検証可能。

柱・小屋束はモデル空間の**ワールド座標**で見つかるが、プラグインオブジェクトの
描画はオブジェクトの**ローカル座標**(挿入点を原点とする座標系)で行われる。この
モジュールは検索で得たワールド座標を挿入点基準のローカル座標へ変換したうえで、
記号を構成する線分を組み立てる。
"""
from __future__ import annotations

from ..document import DOCUMENT_VERSION, Document, MarkCommand

# 記号の既定サイズ (mm)。プラグインパラメータ MarkSize が未設定・0 の場合に使う。
DEFAULT_MARK_SIZE = 300.0


def build_cross_mark(x: float, y: float, size: float) -> MarkCommand:
    """中心 (x, y)・対角長 size の × 記号 (交差する 2 線分) を作る。

    × は中心を通る 2 本の対角線分で表す。size は記号の外接正方形の 1 辺
    (= 各対角線分の水平・垂直方向の伸び) とし、中心から ``size / 2`` ずつ
    四方に伸ばす。
    """
    half = size / 2.0
    return {
        'segments': [
            [[x - half, y - half], [x + half, y + half]],
            [[x - half, y + half], [x + half, y - half]],
        ]
    }


def build_marks(
    positions: list[tuple[float, float]],
    origin: tuple[float, float],
    size: float,
) -> list[MarkCommand]:
    """柱のワールド座標のリストから記号命令のリストを組み立てる。

    ``origin`` はプラグインオブジェクトの挿入点 (ワールド座標)。各柱の位置を
    ``origin`` 基準のローカル座標へ平行移動してから記号を作る。現状は回転
    非対応 (オブジェクトを回転させない前提。CLAUDE.md 参照)。
    """
    if size <= 0:
        size = DEFAULT_MARK_SIZE
    ox, oy = origin
    return [
        build_cross_mark(x - ox, y - oy, size) for x, y in positions
    ]


def build_document(
    positions: list[tuple[float, float]],
    origin: tuple[float, float],
    size: float,
) -> Document:
    """柱のワールド座標から命令セット (Document) を組み立てる。"""
    return {
        'version': DOCUMENT_VERSION,
        'marks': build_marks(positions, origin, size),
    }
