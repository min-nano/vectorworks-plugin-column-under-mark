"""柱の位置から記号 (× 等) のジオメトリを組み立てる。vs 非依存で単体検証可能。

柱・小屋束はモデル空間の**ワールド座標**で見つかるが、プラグインオブジェクトの
描画はオブジェクトの**ローカル座標**(挿入点を原点とする座標系)で行われる。この
モジュールは検索で得たワールド座標を挿入点基準のローカル座標へ変換したうえで、
記号を構成する線分を組み立てる。

記号スタイルによって寸法の決め方が異なる:

- 平面記号 (伏図記号) は挿入点を中心に**指定サイズ** (``MarkSize``) で描く。
  シンボル名 (``MarkSymbol``) を指定した場合は、× / ○ の代わりにそのシンボルを
  各柱位置に配置する (柱・小屋束で共通)。
- 断面記号は柱・小屋束の**実断面** (外接矩形 ``bounds``) に合わせて描く。実断面
  は検索フェーズが ``vs.GetBBox`` で得る。実断面が得られない場合は指定サイズに
  フォールバックする。シンボル指定は断面記号では無視する。
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
    - ``top``: 柱・小屋束の上端の高さ (Z, ワールド座標)。上端高さの範囲
      (``TopRange``) で表示を絞り込むのに使う。取得できなかった場合は ``None``
      (範囲を課さず常に表示)。
    """

    x: float
    y: float
    kind: str
    bounds: Optional[Bounds] = None
    top: Optional[float] = None


class TopRange(NamedTuple):
    """柱・小屋束の上端高さの表示範囲 (下限・上限)。

    伏図で対象としている横架材の下にある柱だけに記号を付けたい、という用途の
    ため、上端が指定範囲に入る柱・小屋束にのみ記号を描く。``minimum`` /
    ``maximum`` はそれぞれ ``None`` の側を無制限とし、両方 ``None`` (既定) なら
    絞り込まない (すべて表示)。境界は含む (``minimum <= top <= maximum``)。
    """

    minimum: Optional[float] = None
    maximum: Optional[float] = None

    def contains(self, top: Optional[float]) -> bool:
        """上端高さ ``top`` がこの範囲に含まれるか判定する。

        ``top`` が ``None`` (高さ不明) の場合は範囲を課さず表示する
        (``True``)。柱が黙って消えて伏図と食い違うのを防ぐため、判定不能なら
        表示側に倒す。``minimum`` / ``maximum`` はそれぞれ ``None`` の側を
        無制限とする。
        """
        if top is None:
            return True
        if self.minimum is not None and top < self.minimum:
            return False
        if self.maximum is not None and top > self.maximum:
            return False
        return True


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
        'symbols': [],
    }


def build_circle_mark(x: float, y: float, size: float) -> MarkCommand:
    """中心 (x, y)・直径 size の ○ 記号 (円 1 個) を作る。

    半径は × 記号の外接正方形と外径をそろえるため ``size / 2`` とする。
    """
    return {
        'segments': [],
        'circles': [{'center': [x, y], 'radius': size / 2.0}],
        'symbols': [],
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
        'symbols': [],
    }


def build_symbol_mark(name: str, x: float, y: float) -> MarkCommand:
    """点 (x, y) にシンボル ``name`` を配置する記号命令を作る。

    平面記号でシンボルを指定した場合に、× / ○ の代わりに用いる。線分・円は
    持たず、シンボル配置 1 個だけを持つ。回転は現状非対応のため付けない
    (描画フェーズが 0 度で配置する)。
    """
    return {
        'segments': [],
        'circles': [],
        'symbols': [{'name': name, 'point': [x, y]}],
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
        'symbols': [],
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
        'symbols': [],
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


def _parse_optional_number(value: str) -> Optional[float]:
    """パラメータ文字列を数値へ変換する。空文字・数値化不能なら ``None``。"""
    text = (value or '').strip()
    if not text:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def normalize_top_range(minimum: str, maximum: str) -> TopRange:
    """上端高さの下限・上限のパラメータ文字列を ``TopRange`` へ正規化する。

    空文字・数値化できない値はその側を無制限 (``None``) とする。両方とも指定
    され下限 > 上限のときは入れ替えて範囲を整合させる (入力ミスに寛容にする)。
    """
    lo = _parse_optional_number(minimum)
    hi = _parse_optional_number(maximum)
    if lo is not None and hi is not None and lo > hi:
        lo, hi = hi, lo
    return TopRange(lo, hi)


def build_mark(
    kind: str, x: float, y: float, size: float,
    style: str = DEFAULT_MARK_STYLE,
    bounds: Optional[Bounds] = None,
    symbol: str = '',
) -> MarkCommand:
    """記号の種類とスタイルに応じた形状を組み立てる。座標はローカル座標。

    - 平面記号 (``STYLE_PLAN``): 中心 (x, y)・指定サイズ。柱→×・小屋束→○。
      ``symbol`` (シンボル名) が空でなければ、× / ○ の代わりにそのシンボルを
      中心 (x, y) に配置する (柱・小屋束で共通)。
    - 断面記号 (``STYLE_SECTION``): 実断面 ``bounds`` (ローカル座標の外接矩形)
      に合わせる。柱→×・小屋束→/。``bounds`` が ``None`` か面積ゼロのときは
      中心 (x, y)・指定サイズにフォールバックする。``symbol`` は断面記号では
      無視する。

    未知のスタイルは平面記号、未知の種類は柱 (×) にフォールバックする。
    """
    # 平面記号 (既定・未知スタイル含む) でシンボル指定があれば、× / ○ の
    # 代わりにシンボルを配置する。断面記号では実断面優先のため無視する。
    if style != STYLE_SECTION and symbol:
        return build_symbol_mark(symbol, x, y)
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
    top_range: TopRange = TopRange(),
    symbol: str = '',
) -> list[MarkCommand]:
    """柱・小屋束の位置情報のリストから記号命令のリストを組み立てる。

    各要素は ``ColumnPosition`` (挿入点・種類・実断面・上端高さ)。``style`` は
    記号スタイル (``STYLE_PLAN`` / ``STYLE_SECTION``)。``top_range`` は上端高さの
    表示範囲で、上端が範囲外の柱・小屋束は記号を作らない (既定は無制限で全表示)。
    ``symbol`` (シンボル名) を指定すると、平面記号では × / ○ の代わりにその
    シンボルを各柱位置に配置する (断面記号では無視)。``origin`` はプラグイン
    オブジェクトの挿入点 (ワールド座標) で、挿入点・実断面ともに ``origin`` 基準の
    ローカル座標へ平行移動してから記号を作る。現状は回転非対応 (オブジェクトを
    回転させない前提。CLAUDE.md 参照)。
    """
    if size <= 0:
        size = DEFAULT_MARK_SIZE
    ox, oy = origin
    marks: list[MarkCommand] = []
    for pos in positions:
        # 上端高さが指定範囲外の柱・小屋束は記号を描かない
        if not top_range.contains(pos.top):
            continue
        local_bounds: Optional[Bounds] = None
        if pos.bounds is not None:
            bx1, by1, bx2, by2 = pos.bounds
            local_bounds = (bx1 - ox, by1 - oy, bx2 - ox, by2 - oy)
        marks.append(
            build_mark(
                pos.kind, pos.x - ox, pos.y - oy, size, style, local_bounds,
                symbol,
            )
        )
    return marks


def build_document(
    positions: list[ColumnPosition],
    origin: tuple[float, float],
    size: float,
    style: str = DEFAULT_MARK_STYLE,
    top_range: TopRange = TopRange(),
    symbol: str = '',
) -> Document:
    """柱・小屋束の位置情報から命令セット (Document) を組み立てる。

    ``top_range`` で上端高さの表示範囲を絞り込む (既定は無制限で全表示)。
    ``symbol`` を指定すると、平面記号では各柱位置にそのシンボルを配置する。
    """
    return {
        'version': DOCUMENT_VERSION,
        'marks': build_marks(positions, origin, size, style, top_range, symbol),
    }
