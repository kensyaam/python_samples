# JSP Analyzer

JSPファイルを解析し、画面構造・データバインディング・ロジック・外部ファイル依存を可視化するPythonスクリプトです。

レガシーシステム（JSP/Spring MVC）からモダンアーキテクチャ（React/Vue等）への移行調査を支援します。

## 機能

| 解析対象 | アイコン | 説明 |
|---|---|---|
| HTML構造 | — | タグのネスト関係をインデント付きツリー表示。標準HTMLタグの `type`/`value` 属性も表示 |
| Spring Formタグ | 🌱 | `<form:input>`, `<form:select>` 等の `path`, `modelAttribute`, `items` を強調表示 |
| JSTL | 💠 | `<c:if>`, `<c:forEach>`, `<c:choose>` 等の制御構文と条件式 |
| EL式 | 🔌 | タグ属性値・テキストノード内の `${...}` を抽出 |
| イベントハンドラ | ⚡ | `onclick`, `onchange` 等と設定値 |
| 静的インクルード | 🔗 | `<%@ include file="..." %>` |
| 動的インクルード | 🔗 | `<jsp:include page="..." />` |
| Javaコード | ☕ | スクリプトレット・式・宣言の埋め込み位置 |
| JavaScript | 📜 | `<script>` タグ（インライン/外部ファイル） |
| JS関数定義 | 🔧 | `<script>` 内の関数定義（function宣言/function式/アロー関数）を一覧抽出 |
| JSイベントバインド | ⚡ | `window.onload`, `addEventListener` 等のJSイベント設定を抽出 |
| 静的テキスト | 📝 | ラベル等のテキストノード |

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
| `--encoding` | — | `utf-8` | JSPファイルの文字エンコーディング（例: `cp932`, `euc-jp`） |
| `--no-text` | — | 表示する | EL式を含まない静的テキスト（ラベル等）を非表示にする |

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
      <h1>
        📝 User Profile
      <🌱form:form> 📦modelAttribute='userForm' method='post' action='/save'
        <div>
          <label>
            📝 Username:
          <🌱form:input> 🔴path='userName' ⚡onchange='validate()'
          <span>
            🔌 [Data]: ${errorMessage}
        <💠c:if> ❓test='${not empty userForm.id}'
          <p>
            🔌 [Data]: ${userForm.id}
            📝 Editing User ID:
      [☕Java Scriptlet]: String debugMsg = "Debug trace"; System.out.pri...
      <📜script> [inline JavaScript]
        🔧 [Functions]: validate
        📝 function validate() { console.log("va...
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
