"""柱・小屋束の位置に記号を描くプラグインオブジェクト。

適当な点に配置すると、指定したレイヤ・クラスの構造材のうち構造用途が柱または
小屋束であるものを検索し、その平面位置に記号 (柱は ×・小屋束は ○) を描く。柱が
編集されればオブジェクトのリセットで記号も追随するため、床伏図・小屋伏図と柱の
食い違いを防げる。

処理は 2 フェーズに分離している (親プロジェクトと同じ思想):

1. 記号ジオメトリ組み立てフェーズ (``core`` パッケージ, vs 非依存)
   柱のワールド座標から、描くべき記号の線分を命令セットとして組み立てる。
2. 検索・描画フェーズ (``vw`` パッケージ, vs 依存)
   指定レイヤ・クラスの柱を検索し、命令セットに従って vs で記号を描く。

命令セットのスキーマは ``document.py`` を参照。
"""
from __future__ import annotations

import json
from typing import Any

from .core import (
    DEFAULT_MARK_SIZE,
    build_document,
    normalize_style,
    normalize_top_range,
)
from .document import validate_document

__all__ = ['build_document', 'run', 'validate_document']

# プラグインオブジェクトのパラメータ (レコードフィールド) 名。
# VectorWorks 側のプラグイン定義でこれらのパラメータを用意すること
# (README 参照)。
PARAM_TARGET_LAYER = 'TargetLayer'   # 検索対象レイヤ (テキスト)
PARAM_TARGET_CLASS = 'TargetClass'   # 検索対象クラス (テキスト)
PARAM_MARK_SIZE = 'MarkSize'         # 記号サイズ (寸法/実数)
PARAM_MARK_STYLE = 'MarkStyle'       # 記号スタイル (平面/断面。テキスト/ポップアップ)
PARAM_TOP_MIN = 'TopHeightMin'       # 上端高さの下限 (寸法/実数)。空欄で無制限
PARAM_TOP_MAX = 'TopHeightMax'       # 上端高さの上限 (寸法/実数)。空欄で無制限


def _parameter(vs: Any, handle: object, record_name: str, field: str) -> str:
    """プラグインオブジェクトのパラメータ値を文字列で取得する。

    レコードにフィールドが無い等で取得できない場合は空文字を返す。
    """
    try:
        value = vs.GetRField(handle, record_name, field)
    except Exception:
        return ''
    return value if isinstance(value, str) else str(value)


def run() -> None:
    """プラグインオブジェクトのリセット (再描画) 処理。

    パラメータ (対象レイヤ・クラス・記号サイズ・記号スタイル・上端高さの範囲)
    を読み取り、該当する柱・小屋束を検索して各位置に記号を描く。上端高さの範囲
    を指定した場合は、上端がその範囲に入る柱・小屋束にのみ記号を描く。
    """
    # vs に依存するモジュールは VectorWorks 上での実行時のみ読み込む。
    # これにより core パッケージ (組み立てフェーズ) は通常の Python 環境でも
    # 利用できる。
    import vs

    from .vw import execute_document, find_column_positions

    # プラグインオブジェクト本体・パラメータレコードのハンドルを取得する。
    # vs.GetCustomObjectInfo() は VectorScript の VAR 引数を含めて 5 値
    # (結果, オブジェクト名, オブジェクトハンドル, レコードハンドル,
    # 壁ハンドル) を返す。
    ok, _name, object_handle, record_handle, _wall = vs.GetCustomObjectInfo()
    if not ok:
        return

    # パラメータレコード名 (= プラグイン名) を得てフィールドを読む
    record_name = vs.GetName(record_handle)
    layer = _parameter(vs, object_handle, record_name, PARAM_TARGET_LAYER)
    class_name = _parameter(vs, object_handle, record_name, PARAM_TARGET_CLASS)
    size_text = _parameter(vs, object_handle, record_name, PARAM_MARK_SIZE)
    try:
        size = float(size_text)
    except (TypeError, ValueError):
        size = DEFAULT_MARK_SIZE
    # 記号スタイル (平面記号=柱×・小屋束○ / 断面記号=柱×・小屋束/)
    style = normalize_style(
        _parameter(vs, object_handle, record_name, PARAM_MARK_STYLE)
    )
    # 上端高さの表示範囲 (下限・上限)。上端が範囲内の柱・小屋束にのみ記号を描く。
    # 空欄の側は無制限、両方空欄なら絞り込まない (すべて表示)。
    top_range = normalize_top_range(
        _parameter(vs, object_handle, record_name, PARAM_TOP_MIN),
        _parameter(vs, object_handle, record_name, PARAM_TOP_MAX),
    )

    # プラグインオブジェクトの挿入点 (記号はこの点を原点とするローカル座標で描く)
    origin = vs.GetSymLoc(object_handle)

    # フェーズ1(検索は vs 依存): 指定レイヤ・クラスの柱を探す
    positions = find_column_positions(layer, class_name)

    # フェーズ1(組み立ては vs 非依存): 柱位置 → 記号命令セット
    document = build_document(positions, origin, size, style, top_range)
    # JSON を経由して命令セットが直列化可能 (= vs ハンドル等を含まない) こと
    # を保証する (親プロジェクトと同じ規約)
    document = json.loads(json.dumps(document))

    # フェーズ2: 命令セットに従って記号を描く
    execute_document(document)
