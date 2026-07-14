"""mark 命令を線分として描画する。vs 依存。

プラグインオブジェクトのリセット時に呼ばれ、記号 (線分) を描く。描いた図形は
VectorWorks がプラグインオブジェクトのジオメトリとして取り込む。座標は
命令セットの時点でローカル座標 (挿入点原点) になっているため、そのまま描く。
"""
from __future__ import annotations

import vs

from ..document import MarkCommand


# 円 (○ 記号) を全周描くための開始角・掃引角 (度)
_CIRCLE_START_ANGLE = 0.0
_CIRCLE_SWEEP_ANGLE = 360.0


def draw_mark(command: MarkCommand) -> None:
    """記号命令 1 件を線分・円の集合として描画する。"""
    for segment in command['segments']:
        (x1, y1), (x2, y2) = segment
        vs.MoveTo(x1, y1)
        vs.LineTo(x2, y2)
    for circle in command['circles']:
        cx, cy = circle['center']
        vs.ArcByCenter(
            cx, cy, circle['radius'],
            _CIRCLE_START_ANGLE, _CIRCLE_SWEEP_ANGLE,
        )


def execute_marks(commands: list[MarkCommand]) -> int:
    """mark 命令のリストを描画し、描画した記号数を返す。"""
    count = 0
    for command in commands:
        draw_mark(command)
        count += 1
    return count
