"""命令セット (ドキュメント) のスキーマ定義と検証。vs / 描画に非依存。

このプラグインオブジェクトの処理も、親プロジェクト
(vectorworks_plugin_import_ifc_homeskz) と同様に **解析フェーズ** と
**描画フェーズ** に分離する。両フェーズは JSON 直列化可能な命令セット
(ドキュメント) だけで接続する。ここではその命令セットの型と検証を定義する。

命令セットの構造::

    {
        "version": 2,
        "marks": [
            {
                "segments": [
                    [[x1, y1], [x2, y2]],   # 線分1本 (始点・終点)
                    [[x3, y3], [x4, y4]],
                    ...
                ],
                "circles": [
                    {"center": [cx, cy], "radius": r},   # 円1個
                    ...
                ]
            },
            ...
        ]
    }

- ``marks``: 描画する記号のリスト。柱・小屋束 1 本につき 1 つの記号。
- 各記号 (``MarkCommand``) は線分 (``segments``) と円 (``circles``) の集合で
  表す。柱の × 記号は交差する 2 本の線分 (円なし)、小屋束の ○ 記号は 1 個の
  円 (線分なし) になる。座標はプラグインオブジェクトのローカル座標 (挿入点を
  原点とする座標系)。解析フェーズが柱のワールド座標をローカル座標へ変換して
  格納するため、描画フェーズは値をそのまま描くだけ。

スキーマを変更するときは ``DOCUMENT_VERSION``・``TypedDict`` 定義・
``validate_document()`` とテストを併せて更新すること。
"""
from __future__ import annotations

from typing import Any, TypedDict

# 命令セットのスキーマバージョン。互換性のない変更時にインクリメントする。
DOCUMENT_VERSION = 2


class CircleCommand(TypedDict):
    """円 1 個の命令。中心座標と半径で表す。"""

    center: list[float]
    radius: float


class MarkCommand(TypedDict):
    """記号 1 個 (柱・小屋束 1 本ぶん) の命令。線分・円の集合で図形を表す。"""

    segments: list[list[list[float]]]
    circles: list[CircleCommand]


class Document(TypedDict):
    """命令セット全体。"""

    version: int
    marks: list[MarkCommand]


def _validate_segment(value: Any) -> list[list[float]]:
    """線分 1 本を検証する。[[x1, y1], [x2, y2]] 形式でなければ例外。"""
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f'線分は始点・終点の 2 点で表してください: {value!r}')
    points: list[list[float]] = []
    for point in value:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError(f'点は [x, y] で表してください: {point!r}')
        x, y = point
        if isinstance(x, bool) or isinstance(y, bool) or \
                not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise ValueError(f'座標は数値で指定してください: {point!r}')
        points.append([float(x), float(y)])
    return points


def _validate_number(value: Any, label: str) -> float:
    """数値を検証して float へ変換する。bool は数値として扱わない。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{label}は数値で指定してください: {value!r}')
    return float(value)


def _validate_circle(value: Any) -> CircleCommand:
    """円 1 個を検証する。{"center": [x, y], "radius": r} 形式でなければ例外。"""
    if not isinstance(value, dict):
        raise ValueError(f'円は dict で指定してください: {value!r}')
    center = value.get('center')
    if not isinstance(center, (list, tuple)) or len(center) != 2:
        raise ValueError(f'円の中心は [x, y] で表してください: {center!r}')
    cx, cy = center
    radius = _validate_number(value.get('radius'), '円の半径')
    if radius <= 0:
        raise ValueError(f'円の半径は正の数で指定してください: {radius!r}')
    return {
        'center': [_validate_number(cx, '座標'), _validate_number(cy, '座標')],
        'radius': radius,
    }


def _validate_mark(value: Any) -> MarkCommand:
    """記号命令 1 件を検証する。segments・circles はどちらも省略可 (既定 [])。"""
    if not isinstance(value, dict):
        raise ValueError(f'記号命令は dict で指定してください: {value!r}')
    segments = value.get('segments', [])
    if not isinstance(segments, (list, tuple)):
        raise ValueError(f'segments はリストで指定してください: {value!r}')
    circles = value.get('circles', [])
    if not isinstance(circles, (list, tuple)):
        raise ValueError(f'circles はリストで指定してください: {value!r}')
    return {
        'segments': [_validate_segment(segment) for segment in segments],
        'circles': [_validate_circle(circle) for circle in circles],
    }


def validate_document(document: Any) -> Document:
    """JSON 由来の信頼できない命令セットを検証し、Document 型として返す。

    version がスキーマと非互換、または marks の形式が不正な場合は
    ValueError を送出する。
    """
    if not isinstance(document, dict):
        raise ValueError('命令セットは dict で指定してください。')
    version = document.get('version')
    if version != DOCUMENT_VERSION:
        raise ValueError(
            f'命令セットのバージョンが非対応です: {version!r} '
            f'(対応: {DOCUMENT_VERSION})'
        )
    marks = document.get('marks')
    if not isinstance(marks, (list, tuple)):
        raise ValueError('marks はリストで指定してください。')
    return {
        'version': DOCUMENT_VERSION,
        'marks': [_validate_mark(mark) for mark in marks],
    }
