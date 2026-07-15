"""柱の位置から記号 (× 等) のジオメトリを組み立てる。vs 非依存で単体検証可能。

柱・小屋束はモデル空間の**ワールド座標**で見つかるが、プラグインオブジェクトの
描画はオブジェクトの**ローカル座標**(挿入点を原点とする座標系)で行われる。この
モジュールは検索で得たワールド座標を挿入点基準のローカル座標へ変換したうえで、
記号を構成する線分を組み立てる。
"""
from __future__ import annotations

from typing import Callable

from ..document import DOCUMENT_VERSION, Document, MarkCommand

# 記号の既定サイズ (mm)。プラグインパラメータ MarkSize が未設定・0 の場合に使う。
DEFAULT_MARK_SIZE = 300.0

# 記号の種類。検索フェーズ (vw/search.py) が構造用途 (柱="4"・小屋束="5") を
# この種類に変換し、組み立てフェーズが種類・記号スタイルごとに記号形状を選ぶ。
KIND_COLUMN = 'column'
KIND_KOYAZUKA = 'koyazuka'

# 記号のスタイル。プラグインパラメータ MarkStyle で選択する。
# - 平面記号 (STYLE_PLAN, 既定): 柱=×・小屋束=○
# - 断面記号 (STYLE_SECTION):    柱=×・小屋束=/ (対角線 1 本)
# 柱はどちらのスタイルでも × のまま。小屋束の形状だけが変わる。
STYLE_PLAN = 'plan'
STYLE_SECTION = 'section'
DEFAULT_MARK_STYLE = STYLE_PLAN


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
        ],
        'circles': [],
    }


def build_circle_mark(x: float, y: float, size: float) -> MarkCommand:
    """中心 (x, y)・直径 size の ○ 記号 (円 1 個) を作る。

    半径は × 記号の外接正方形と外径をそろえるため ``size / 2`` とする。
    """
    return {
        'segments': [],
        'circles': [{'center': [x, y], 'radius': size / 2.0}],
    }


def build_diagonal_mark(x: float, y: float, size: float) -> MarkCommand:
    """中心 (x, y)・対角長 size の / 記号 (対角線 1 本) を作る。

    断面記号での小屋束を表す。× 記号 (2 本) のうち左下→右上の 1 本だけを
    描いたものに相当する。
    """
    half = size / 2.0
    return {
        'segments': [
            [[x - half, y - half], [x + half, y + half]],
        ],
        'circles': [],
    }


# 記号スタイル → (種類 → 形状ビルダー)。未知の種類は柱扱い (×) にフォール
# バックする。柱はどのスタイルでも × のまま、小屋束の形状だけが変わる。
_STYLE_MARK_BUILDERS: dict[
    str, dict[str, Callable[[float, float, float], MarkCommand]]
] = {
    STYLE_PLAN: {
        KIND_COLUMN: build_cross_mark,
        KIND_KOYAZUKA: build_circle_mark,
    },
    STYLE_SECTION: {
        KIND_COLUMN: build_cross_mark,
        KIND_KOYAZUKA: build_diagonal_mark,
    },
}

# 断面記号を表すパラメータ文字列のトークン (大文字小文字は無視)。
_SECTION_TOKENS = ('section', '断面')


def normalize_style(value: str) -> str:
    """記号スタイルのパラメータ文字列を既知のスタイルへ正規化する。

    '断面'・'section' を含む場合は ``STYLE_SECTION``、それ以外 (空文字含む) は
    既定の ``STYLE_PLAN`` を返す。VectorWorks 側のパラメータ表記ゆれを吸収する。
    """
    text = (value or '').strip()
    lowered = text.lower()
    if any(token in text or token in lowered for token in _SECTION_TOKENS):
        return STYLE_SECTION
    return STYLE_PLAN


def build_mark(
    kind: str, x: float, y: float, size: float,
    style: str = DEFAULT_MARK_STYLE,
) -> MarkCommand:
    """記号の種類とスタイルに応じた形状を組み立てる。

    平面記号 (``STYLE_PLAN``) は柱→×・小屋束→○、断面記号 (``STYLE_SECTION``)
    は柱→×・小屋束→/。未知のスタイルは平面記号にフォールバックする。
    """
    builders = _STYLE_MARK_BUILDERS.get(style, _STYLE_MARK_BUILDERS[STYLE_PLAN])
    builder = builders.get(kind, build_cross_mark)
    return builder(x, y, size)


def build_marks(
    positions: list[tuple[float, float, str]],
    origin: tuple[float, float],
    size: float,
    style: str = DEFAULT_MARK_STYLE,
) -> list[MarkCommand]:
    """柱・小屋束の位置と種類のリストから記号命令のリストを組み立てる。

    各要素は ``(x, y, kind)`` で、``kind`` は記号の種類 (``KIND_COLUMN`` /
    ``KIND_KOYAZUKA``)。``style`` は記号スタイル (``STYLE_PLAN`` /
    ``STYLE_SECTION``)。``origin`` はプラグインオブジェクトの挿入点 (ワールド
    座標) で、各位置を ``origin`` 基準のローカル座標へ平行移動してから記号を
    作る。現状は回転非対応 (オブジェクトを回転させない前提。CLAUDE.md 参照)。
    """
    if size <= 0:
        size = DEFAULT_MARK_SIZE
    ox, oy = origin
    return [
        build_mark(kind, x - ox, y - oy, size, style)
        for x, y, kind in positions
    ]


def build_document(
    positions: list[tuple[float, float, str]],
    origin: tuple[float, float],
    size: float,
    style: str = DEFAULT_MARK_STYLE,
) -> Document:
    """柱・小屋束の位置と種類から命令セット (Document) を組み立てる。"""
    return {
        'version': DOCUMENT_VERSION,
        'marks': build_marks(positions, origin, size, style),
    }
