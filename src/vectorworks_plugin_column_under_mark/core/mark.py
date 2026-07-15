"""柱の位置から記号 (× 等) のジオメトリを組み立てる。vs 非依存で単体検証可能。

柱・小屋束はモデル空間の**ワールド座標**で見つかるが、プラグインオブジェクトの
描画はオブジェクトの**ローカル座標**(挿入点を原点とする座標系)で行われる。この
モジュールは検索で得たワールド座標を挿入点基準のローカル座標へ変換したうえで、
記号を構成する線分を組み立てる。

記号スタイルによって寸法の決め方が異なる:

- 平面記号 (伏図記号) は挿入点を中心に**指定サイズ** (``MarkSize``) で描く。
- 断面記号は柱・小屋束の**実断面** (外接矩形 ``bounds``) に合わせて描く。実断面
  は検索フェーズが ``vs.GetBBox`` で得る。実断面が得られない場合は指定サイズに
  フォールバックする。
"""
from __future__ import annotations

from typing import Callable, NamedTuple, Optional

from ..document import DOCUMENT_VERSION, Document, MarkCommand

# 記号の既定サイズ (mm)。プラグインパラメータ MarkSize が未設定・0 の場合に使う。
DEFAULT_MARK_SIZE = 300.0

# 記号の種類。検索フェーズ (vw/search.py) が構造用途 (柱="4"・小屋束="5") を
# この種類に変換し、組み立てフェーズが種類・記号スタイルごとに記号形状を選ぶ。
KIND_COLUMN = 'column'
KIND_KOYAZUKA = 'koyazuka'

# 記号のスタイル。プラグインパラメータ MarkStyle で選択する。
# - 平面記号 (STYLE_PLAN, 既定): 柱=×・小屋束=○。挿入点中心・指定サイズ。
# - 断面記号 (STYLE_SECTION):    柱=×・小屋束=/ (対角線 1 本)。実断面に合わせる。
# 柱はどちらのスタイルでも × のまま。小屋束の形状だけが変わる。
STYLE_PLAN = 'plan'
STYLE_SECTION = 'section'
DEFAULT_MARK_STYLE = STYLE_PLAN

# 実断面の外接矩形 (ワールド座標)。対角する 2 隅 (x1, y1)-(x2, y2)。隅の並び順
# (左上/右下など) は問わない (ビルダー側で min/max を取る)。
Bounds = tuple[float, float, float, float]


class ColumnPosition(NamedTuple):
    """検索フェーズが返す柱・小屋束 1 本ぶんの情報。

    - ``x`` / ``y``: 挿入点 (ワールド座標)。平面記号の中心に使う。
    - ``kind``: 記号の種類 (``KIND_COLUMN`` / ``KIND_KOYAZUKA``)。
    - ``bounds``: 実断面の外接矩形 (ワールド座標)。断面記号で使う。取得でき
      なかった場合は ``None`` (断面記号は指定サイズにフォールバック)。
    """

    x: float
    y: float
    kind: str
    bounds: Optional[Bounds] = None


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
    描いたものに相当する。実断面が得られない場合のフォールバックに使う。
    """
    half = size / 2.0
    return {
        'segments': [
            [[x - half, y - half], [x + half, y + half]],
        ],
        'circles': [],
    }


def build_cross_in_bounds(
    x1: float, y1: float, x2: float, y2: float
) -> MarkCommand:
    """外接矩形 (x1, y1)-(x2, y2) の対角線 2 本で × を作る (断面記号の柱)。

    実断面の 4 隅を結ぶ 2 本の対角線で、記号を実断面の寸法・位置に合わせる。
    """
    return {
        'segments': [
            [[x1, y1], [x2, y2]],
            [[x1, y2], [x2, y1]],
        ],
        'circles': [],
    }


def build_diagonal_in_bounds(
    x1: float, y1: float, x2: float, y2: float
) -> MarkCommand:
    """外接矩形 (x1, y1)-(x2, y2) の対角線 1 本 (左下→右上) で / を作る。

    断面記号の小屋束。隅の並び順に依らず左下→右上に揃えるため min/max を取る。
    """
    lo_x, hi_x = (x1, x2) if x1 <= x2 else (x2, x1)
    lo_y, hi_y = (y1, y2) if y1 <= y2 else (y2, y1)
    return {
        'segments': [[[lo_x, lo_y], [hi_x, hi_y]]],
        'circles': [],
    }


# 平面記号 (伏図記号): 挿入点中心・指定サイズ。柱=×・小屋束=○。
# 未知の種類は柱扱い (×) にフォールバックする。
_PLAN_BUILDERS: dict[str, Callable[[float, float, float], MarkCommand]] = {
    KIND_COLUMN: build_cross_mark,
    KIND_KOYAZUKA: build_circle_mark,
}

# 断面記号: 実断面 (外接矩形) に合わせる。柱=×・小屋束=/。
_SECTION_BOUNDS_BUILDERS: dict[
    str, Callable[[float, float, float, float], MarkCommand]
] = {
    KIND_COLUMN: build_cross_in_bounds,
    KIND_KOYAZUKA: build_diagonal_in_bounds,
}

# 断面記号で実断面が得られない (bounds 無し/面積ゼロ) 場合の指定サイズ
# フォールバック。柱=×・小屋束=/。
_SECTION_SIZE_BUILDERS: dict[str, Callable[[float, float, float], MarkCommand]] = {
    KIND_COLUMN: build_cross_mark,
    KIND_KOYAZUKA: build_diagonal_mark,
}

# 断面記号を表すパラメータ文字列のトークン (大文字小文字は無視)。
_SECTION_TOKENS = ('section', '断面')


def _bounds_has_area(bounds: Bounds) -> bool:
    """外接矩形が幅・高さともに正の広がりを持つか (対角線を引けるか) を判定する。"""
    x1, y1, x2, y2 = bounds
    return x1 != x2 and y1 != y2


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
    bounds: Optional[Bounds] = None,
) -> MarkCommand:
    """記号の種類とスタイルに応じた形状を組み立てる。座標はローカル座標。

    - 平面記号 (``STYLE_PLAN``): 中心 (x, y)・指定サイズ。柱→×・小屋束→○。
    - 断面記号 (``STYLE_SECTION``): 実断面 ``bounds`` (ローカル座標の外接矩形)
      に合わせる。柱→×・小屋束→/。``bounds`` が ``None`` か面積ゼロのときは
      中心 (x, y)・指定サイズにフォールバックする。

    未知のスタイルは平面記号、未知の種類は柱 (×) にフォールバックする。
    """
    if style == STYLE_SECTION:
        if bounds is not None and _bounds_has_area(bounds):
            bounds_builder = _SECTION_BOUNDS_BUILDERS.get(
                kind, build_cross_in_bounds
            )
            return bounds_builder(*bounds)
        size_builder = _SECTION_SIZE_BUILDERS.get(kind, build_cross_mark)
        return size_builder(x, y, size)
    plan_builder = _PLAN_BUILDERS.get(kind, build_cross_mark)
    return plan_builder(x, y, size)


def build_marks(
    positions: list[ColumnPosition],
    origin: tuple[float, float],
    size: float,
    style: str = DEFAULT_MARK_STYLE,
) -> list[MarkCommand]:
    """柱・小屋束の位置情報のリストから記号命令のリストを組み立てる。

    各要素は ``ColumnPosition`` (挿入点・種類・実断面)。``style`` は記号スタイル
    (``STYLE_PLAN`` / ``STYLE_SECTION``)。``origin`` はプラグインオブジェクトの
    挿入点 (ワールド座標) で、挿入点・実断面ともに ``origin`` 基準のローカル座標
    へ平行移動してから記号を作る。現状は回転非対応 (オブジェクトを回転させない
    前提。CLAUDE.md 参照)。
    """
    if size <= 0:
        size = DEFAULT_MARK_SIZE
    ox, oy = origin
    marks: list[MarkCommand] = []
    for pos in positions:
        local_bounds: Optional[Bounds] = None
        if pos.bounds is not None:
            bx1, by1, bx2, by2 = pos.bounds
            local_bounds = (bx1 - ox, by1 - oy, bx2 - ox, by2 - oy)
        marks.append(
            build_mark(
                pos.kind, pos.x - ox, pos.y - oy, size, style, local_bounds
            )
        )
    return marks


def build_document(
    positions: list[ColumnPosition],
    origin: tuple[float, float],
    size: float,
    style: str = DEFAULT_MARK_STYLE,
) -> Document:
    """柱・小屋束の位置情報から命令セット (Document) を組み立てる。"""
    return {
        'version': DOCUMENT_VERSION,
        'marks': build_marks(positions, origin, size, style),
    }
