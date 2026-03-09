# JSP Analyzer

JSPファイルを解析し、画面構造・データバインディング・ロジック・外部ファイル依存を可視化するPythonスクリプトです。

レガシーシステム（JSP/Spring MVC）からモダンアーキテクチャ（React/Vue等）への移行調査を支援します。

## 機能

| 解析対象 | アイコン | 説明 |
|---|---|---|
| HTML構造 | — | タグのネスト関係をインデント付きツリー表示。標準HTMLタグの `type`/`value`/`name` 属性も表示（`name` 属性は 🔴 で表示） |
| Spring Formタグ | 🌱 | `<form:input>`, `<form:select>` 等の `path`, `modelAttribute`, `items` を強調表示（`path` 属性は 🔴 で表示） |
| JSTL | 💠 | `<c:if>`, `<c:forEach>`, `<c:choose>` 等の制御構文と条件式 |
| EL式 | 🧩 | タグ属性値・テキストノード内の `${...}` を抽出 |
| イベントハンドラ | ⚡ | `onclick`, `onchange` 等と設定値 |
| 静的インクルード | 🔗 | `<%@ include file="..." %>` |
| 動的インクルード | 🔗 | `<jsp:include page="..." />` |
| Javaコード | ☕ | スクリプトレット・式・宣言の埋め込み位置 |
| JavaScript | 📜 | `<script>` タグ（インライン/外部ファイル） |
| JS関数定義 | 🔧 | `<script>` 内の関数定義（function宣言/function式/アロー関数）を一覧抽出 |
| JSイベントバインド | ⚡ | `window.onload`, `addEventListener` 等のJSイベント設定を抽出 |
| 静的テキスト | 📝 | ラベル等のテキストノード |

### 🚨 移行支援 / 警告機能

JSPからモダンフロントエンドへの移行時に「手作業での対応が必要な箇所」を自動で検出し、警告マーク（🔥）と共にリストアップします。
標準では、スクリプトレット、JSの直接記述、非推奨HTMLタグなどが検出されます。

*   **カスタマイズ可能な抽出ルール**: `jsp_analyzer.py` 内の `DEFAULT_MIGRATION_RULES` を編集することで、プロジェクト独自のルール（特定のタグや正規表現パターン）を追加可能です。
*   **サマリーレポート**: 解析終了時に全ファイルの統計情報（ルール別・ファイル別の検出数）をコンソールに出力します。
*   **CSV出力 (移行ToDoリスト)**: 解析結果を一覧化・共有しやすいCSV形式で一括出力できます。

## 必要環境

- Python 3.8以上
- BeautifulSoup4

## インストール

```bash
pip install -r requirements.txt
```

## 使い方

```bash
python jsp_analyzer.py [input_dir] [--output-dir OUTPUT_DIR] [--encoding ENCODING] [--no-text]
```

### 引数

| 引数 | 必須 | デフォルト | 説明 |
|---|---|---|---|
| `input_dir` | ✅ | — | 解析対象のディレクトリパス |
| `--output-dir` | — | なし | 解析結果の出力先ディレクトリ（`.jsp.txt` ファイルを生成） |
| `--csv-output` | — | なし | 移行必須リストのCSVファイル出力先パス（例: `report.csv`） |
| `--encoding` | — | `utf-8` | JSPファイルの文字エンコーディング（例: `cp932`, `euc-jp`） |
| `--no-text` | — | 表示する | EL式を含まない静的テキスト（ラベル等）を非表示にする |
| `--show-rules` | — | 表示しない | 現在設定されている移行支援の警告ルール一覧を表示して終了する |

### 実行例

**基本実行（コンソール出力のみ）:**

```bash
python jsp_analyzer.py test_jsp
```

**ファイル出力付き:**

```bash
python jsp_analyzer.py test_jsp --output-dir output
```

入力ディレクトリの階層構造を維持して `.jsp.txt` ファイルが生成されます。

**CSVレポート（移行リスト）の出力:**

```bash
python jsp_analyzer.py test_jsp --output-dir output --csv-output output/migration_report.csv
```

**現在の警告ルールを確認する:**

```bash
python jsp_analyzer.py --show-rules
```

**Shift-JISのJSPファイルを解析:**

```bash
python jsp_analyzer.py legacy_project/WEB-INF/jsp --encoding cp932
```

**静的テキストを非表示にして解析:**

```bash
python jsp_analyzer.py test_jsp --no-text
```

## 出力フォーマット例

```text
=== Analysis Result for: test_jsp/sample.jsp ===
<[document]>
  <🔗Static Include> file='header.jsp'
  <html>
    <body>
      🔥 [低] <center>
        <h1>
          🔥 [低] <font>
            📝 User Profile
      <🌱form:form> 📦modelAttribute='userForm' method='post' action='/save'
        <div>
          <input> type='hidden' 🔴name='action' value='update'
          <label>
            📝 Username:
          <🌱form:input> 🔴path='userName' 🔥 [低] ⚡onchange='validate()'
          <span>
            🧩 ${errorMessage}
        <💠c:if> ❓test='🧩${not empty userForm.id}'
          <p>
            🧩 ${userForm.id}
            📝 Editing User ID:
      🔥 [高] [☕Java Scriptlet]: <% String debugMsg="Debug trace" ; System.out.println(debugMsg); %>
      <📜script> [inline JavaScript]
        🔥 [中] 🔧 [Function]: validate
        📝 function validate() { console.log("validating..."); }
```

末尾にはサマリーレポートが出力されます。

```text
============================================================
【移行タスク サマリーレポート】
============================================================
対象ファイル数: 1
要注意箇所(全体): 4 件

[ルール別 検出数 内訳]
  スクリプトレット        (難易度: 高):    1件 - バックエンドAPI等への移行が必要
  JS関数定義          (難易度: 中):    1件 - コンポーネント内メソッド等への移行が必要
  非推奨HTMLタグ       (難易度: 低):    1件 - CSSでのスタイリングへ移行が必要
  インラインイベント       (難易度: 低):    1件 - JSXのイベントハンドラ(onClick等)へ移行
...
```

## 前処理（JSP → HTML変換）

BeautifulSoupでパースする前に、JSP特有の構文を正規表現で前処理します：

| JSP構文 | 変換先 |
|---|---|
| `<%-- ... --%>` | 削除（JSPコメント） |
| `<%@ include file="..." %>` | `<jsp-static-include file="..." />` |
| `<%@ page ... %>`, `<%@ taglib ... %>` | 削除（構造破壊防止） |
| `<% ... %>` | `<jsp-logic type="scriptlet">...</jsp-logic>` |
| `<%= ... %>` | `<jsp-logic type="expression">...</jsp-logic>` |
| `<%! ... %>` | `<jsp-logic type="declaration">...</jsp-logic>` |

## 制限・注意事項

- BeautifulSoupの `html.parser` がタグ名・属性名を小文字化しますが、主要なJSTL/FMTタグ（`c:forEach`, `fmt:formatNumber` 等）は内部マッピングにより元のキャメルケース表記で出力されます。マッピングに含まれないカスタムタグ名は小文字で表示される場合があります
- EL式の中身の構文解析は行いません（正規表現 `${...}` によるパターンマッチのみ）
- カスタムタグライブラリ（独自タグ）は通常のHTMLタグとして表示されます
- JSPフラグメント (`.jspf`) は検索対象外です（`.jsp` のみ）

## 開発

```bash
# 開発用依存関係のインストール
pip install -r requirements-dev.txt

# Blackでフォーマット
black jsp_analyzer.py

# mypyで型チェック
mypy jsp_analyzer.py

# flake8でリント
flake8 jsp_analyzer.py
```
