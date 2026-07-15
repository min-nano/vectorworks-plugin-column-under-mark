# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## このリポジトリについて

指定したレイヤ・クラスの構造材のうち**構造用途が柱または小屋束**であるものを
検索し、その平面位置に記号 (○・× 等) を描く VectorWorks の**プラグイン
オブジェクト (ポイントオブジェクト)** です。適当な点に配置すると対象の柱を探して
各柱位置に記号を描画し、柱が編集されればオブジェクトのリセットで記号の位置・数が
追随します。床伏図・小屋伏図と柱の食い違いを防ぐことが目的です。

姉妹プロジェクト `vectorworks_plugin_import_ifc_homeskz` (ホームズ君 IFC を
VectorWorks に取り込むプラグイン) が配置した柱を対象に想定しています。あちらの
柱・小屋束は構造材ツール (`StructuralMember`) で描かれ、構造用途
(`StructuralUse` レコードフィールド) が柱="4"・小屋束="5" になります。

現在実装済みの機能:

- 指定レイヤ・クラスの柱・小屋束 (構造用途 4/5) の検索
- 柱位置への × 記号 (2 本の線分) の描画
- 記号スタイル (`MarkStyle` パラメータ) の選択。平面記号 (既定) では小屋束を
  ○ 記号 (円)、断面記号では小屋束を / 記号 (対角線 1 本) で描く。柱はどちらの
  スタイルでも × のまま。

今後の予定:

- プラグインオブジェクトを回転配置した場合の記号の向き補正

## 登録形態: ラッパースクリプト方式

姉妹プロジェクトと同様に、VectorWorks に登録するのは**ラッパースクリプト
`main.py` だけ**で、本体は実行時に GitHub の `main` ブランチ最新コミットを
ダウンロードして実行する。`main.py` は姉妹プロジェクトからほぼそのまま流用し、
`PACKAGE_NAME`・`MODULE_NAME`・`REPOSITORY`・`DEPENDENCIES` だけを差し替えて
いる (本体は certifi 以外の外部依存を持たない。certifi は自動更新の HTTPS
アクセス用)。更新判定はコミット SHA、オフライン時はインストール済みを実行する。
`main.py` を変更するときは姉妹プロジェクトの `main.py` との差分が最小になるよう
保つこと。

**プラグインオブジェクトのリセットのたびに** `main.py` が実行され、更新確認 →
本体 import → `run()` が走る。`run()` がリセット (再描画) ハンドラであり、記号を
描き直す。

## アーキテクチャ: 2 フェーズ分離

姉妹プロジェクトの「IFC 解析フェーズ / VectorWorks 描画フェーズ」の分離思想を
踏襲する。両フェーズは JSON 直列化可能な**命令セット (ドキュメント)** だけで
接続し、`vs` との密結合を避ける。

1. **記号ジオメトリ組み立てフェーズ (`core` サブパッケージ)** — `vs` に一切
   依存しない。柱のワールド座標から、描くべき記号を構成する線分を命令セット
   (dict) として組み立てる。通常の Python 環境で単体検証できる。
2. **検索・描画フェーズ (`vw` サブパッケージ)** — `vs` だけに依存する。指定
   レイヤ・クラスの柱を検索し (`vw/search.py`)、命令セットを検証
   (`validate_document`) してから vs API で記号を描く (`vw/draw.py`)。

姉妹プロジェクトとの違い: あちらは IFC 解析 (`ifc`, vs 非依存) と描画 (`vw`,
vs 依存) の 2 フェーズだが、こちらは**柱の検索そのものが vs に依存する**ため、
検索は `vw` サブパッケージに置く。vs 非依存で単体検証できるのは「柱位置 → 記号
ジオメトリ」の組み立て (`core`) と命令セットの検証 (`document.py`) の部分。

`run()` は検索 (vw) で柱のワールド座標を得たあと、`core.build_document` で命令
セットを組み立て、`json.dumps`/`json.loads` を通してから `vw.execute_document`
で描画する。命令セットに直列化不能なオブジェクト (vs ハンドル等) を入れては
ならない。

## パッケージ構造

```
src/
    vectorworks_plugin_column_under_mark/   # pip インストール可能なパッケージ本体
        __init__.py       # run() を公開 (パラメータ読取 → 検索 → 命令セット → 描画)
        document.py       # 命令セットのスキーマ定義・検証 (vs 非依存)
        core/             # フェーズ1: 記号ジオメトリ組み立て (vs 非依存)
            __init__.py   # build_document / build_marks / build_mark / 記号種類・スタイル定数を公開
            mark.py       # 柱・小屋束の位置と種類・スタイル → mark 命令 (× と ○ は線分/円、断面は / の線分)
        vw/               # フェーズ2: 検索・描画 (vs 依存)
            __init__.py   # execute_document(document) / find_column_positions を公開
            search.py     # 指定レイヤ・クラスの柱 (構造用途 4/5) を検索 → 位置
            draw.py       # mark 命令 → 線分 (MoveTo/LineTo) を描画
main.py                  # VectorWorks に登録するラッパースクリプト (実行時に自動更新)
tests/                   # pytest 用テスト (CI は vs.py スタブを GitHub からダウンロード)
pyproject.toml           # パッケージメタデータ
```

`vs` を import してよいのは `vw` サブパッケージ内・`run()` 関数内だけ。`core`
サブパッケージや `document.py` に `vs` への依存を持ち込まないこと。テストも
この分離に従う: `tests/test_core_mark.py`・`tests/test_document.py` は vs モック
不要、`tests/test_vw_*.py`・`tests/test_init.py` は vs モックで実行して検証する。

## 命令セットのスキーマ

命令セット (`document.py`) の構造:

```
{
    "version": 2,
    "marks": [
        # 記号1個 = 線分の集合 (segments) + 円の集合 (circles)
        {
            "segments": [[[x1, y1], [x2, y2]], ...],
            "circles": [{"center": [cx, cy], "radius": r}, ...]
        },
        ...
    ]
}
```

- `marks`: 柱・小屋束 1 本につき 1 つの記号 (`MarkCommand`)。
- 各記号は線分 (`segments`) と円 (`circles`) の集合。柱の × 記号は交差する
  2 本の線分 (円なし)、小屋束の ○ 記号は 1 個の円 (線分なし)。`segments` /
  `circles` はどちらも省略可能 (検証時に既定 `[]`)。
- 座標は**プラグインオブジェクトのローカル座標** (挿入点を原点とする座標系)。
  組み立てフェーズ (`core/mark.py`) が柱のワールド座標から挿入点を差し引いて
  格納するため、描画フェーズはそのまま描くだけ。

スキーマを変更するときは `DOCUMENT_VERSION`・`TypedDict` 定義 (`MarkCommand` /
`CircleCommand` / `Document`)・`validate_document()`・docstring・テストを
併せて更新すること。

## 座標系: ローカル座標への変換

**プラグインオブジェクトのジオメトリは、オブジェクトの挿入点を原点とする
ローカル座標で描かれる。** 一方、柱はモデル空間のワールド座標で見つかる。この
ため `core/mark.py` の `build_marks` は柱のワールド座標から挿入点 (`origin`) を
差し引いてローカル座標に直してから記号を作る。挿入点は `run()` が
`vs.GetSymLoc(object_handle)` で取得する。

現状は**オブジェクトを回転させない前提** (平行移動のみ)。回転して配置した場合は
記号の位置がずれる。回転対応 (`vs.GetSymRot` で角度を得て逆回転) は今後の課題。
ローカル座標への変換が正しいか (プラグインオブジェクトが実際にローカル座標で
描画されるか) は VectorWorks 上で最終確認する方針。

## 柱の検索 (vw/search.py)

- 検索条件式 (`build_criteria`) はプラグインオブジェクト名
  (`(PON='StructuralMember')`)・レイヤ (`(L='…')`)・クラス (`(C='…')`) で絞る。
  レイヤ・クラスが空文字ならその条件を付けない (全対象)。構造用途は条件式では
  絞れないためコールバック側で判定する。
- `vs.ForEachObject(callback, criteria)` で構造材を走査し、コールバックで構造
  用途 (`GetRField(h, 'StructuralMember', 'StructuralUse')`) を記号の種類に変換
  する (`column_kind`): 柱="4" → `KIND_COLUMN`、小屋束="5" → `KIND_KOYAZUKA`、
  どちらでもなければ `None` (対象外)。`find_column_positions` は対象だけを
  `(x, y, kind)` の形で返し、`core` が種類と記号スタイルごとに記号形状 (柱→×・
  小屋束→平面記号なら ○/断面記号なら /) を選ぶ。記号種類の定数
  (`KIND_COLUMN` / `KIND_KOYAZUKA`) は vs 非依存の `core`
  側で定義し、`search` が import する (種類→形状の対応付けは presentation で
  あり `core` が持つ)。
- 位置は構造材 (プラグインオブジェクト) の挿入点 `vs.GetSymLoc(h)` を用いる。
- 構造用途の値 (柱="4"・小屋束="5") は姉妹プロジェクトの `vw/column.py` が
  `StructuralUse` フィールドに設定する値と一致させている。VectorWorks の構造材
  ツール・条件式の実挙動は VW 上で最終確認する方針。

## パラメータの読取 (run)

`run()` は `vs.GetCustomObjectInfo()` でプラグインオブジェクト本体・パラメータ
レコードのハンドルを取得し、`vs.GetName(record_handle)` でレコード名 (=プラグ
イン名) を得て、`vs.GetRField` で各パラメータを読む。パラメータのフィールド名は
`__init__.py` の定数 (`PARAM_TARGET_LAYER`='TargetLayer' /
`PARAM_TARGET_CLASS`='TargetClass' / `PARAM_MARK_SIZE`='MarkSize' /
`PARAM_MARK_STYLE`='MarkStyle') に集約している。VectorWorks 側のプラグイン
定義でこれらのパラメータを用意する必要がある (README 参照)。`MarkSize` が
数値に解釈できない場合は既定サイズ (`core/mark.py` の `DEFAULT_MARK_SIZE`
=300mm) にフォールバックする。`MarkStyle` は `core.normalize_style` で正規化
し、'断面'・'section' を含めば断面記号 (`STYLE_SECTION`)、それ以外・空欄なら
平面記号 (`STYLE_PLAN`、既定) を使う。記号スタイル → 種類 → 形状の対応付けは
presentation として `core/mark.py` の `_STYLE_MARK_BUILDERS` が持つ。

## コーディング規約: 型注釈

姉妹プロジェクトと同じ。すべての関数・メソッド (テストコード・モック用クロージャ
含む) に引数と戻り値の型注釈を付ける。型検査は mypy (`pyproject.toml` の
`[tool.mypy]`、`disallow_untyped_defs` 有効)、CI で実行する。

- 各モジュール先頭に `from __future__ import annotations` を置く (Python 3.9
  互換で `list[str]` / `X | None` 構文を使うため)。
- 命令セットの型は `document.py` の `TypedDict` (`Document` / `MarkCommand`)。
  `class` 等の予約語キーを持たないため通常の `class` 構文で定義する。
- `vs` モジュールは型スタブが無いため `ignore_missing_imports` で許容し、vs
  ハンドルは `object` / `Any` で扱う。公式 `vs.py` スタブ (`tests/vs.py`) は
  型検査対象から除外する。
- 検証前の命令セット (JSON 由来の信頼できない入力) を受ける関数
  (`validate_document` / `execute_document`) の引数は `Any` とし、検証済みの
  値だけを `Document` 型として扱う。

## テストの実行方法

このスクリプトは単独の Python プログラムとしては動作せず、**VectorWorks 内で
プラグインオブジェクトとして実行する必要がある**。`vs` モジュールは VectorWorks
独自の API で pip インストールできない。テストは VectorWorks 公式 `vs.py`
スタブをモック対象として `pytest` で実行する (`.github/workflows/test.yml`
参照)。CI は Python 3.9 / 3.11 で mypy と pytest を実行する。

## 開発プロセス: PR 作成と監視

コード修正を実施する際は以下のプロセスに従う:

1. **PR作成の判断基準**:
   - コード編集後、ユーザーに確認すべき疑義が特にない場合は**自動的に PR を
     作成する**。
   - 迷いや未確定事項がある場合は PR 作成を保留し先にユーザーに確認する。
2. **PR 作成後の対応**:
   - PR を作成したら `subscribe_pr_activity` で CI 結果とレビューコメントを
     監視する。CI 失敗は原因を診断して修正コミットを push する。レビュー
     コメントは軽微なら自動修正、大きな変更・設計判断はユーザーに確認する。
   - CI が全て green でレビュー上の問題もなければ自動的にマージする。
3. **コミットメッセージ**:
   - Claude セッション URL を追加する形式: `https://claude.ai/code/session_<SESSION_ID>`
