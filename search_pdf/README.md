# PDF文字列検索ツール

指定した文字列でPDFファイルの内容を一括検索し、結果をCSV形式で出力するCLIツールです。

## 事前準備

```bash
# 仮想環境の作成、有効化
python -m venv .venv
source .venv/Scripts/activate

# 依存パッケージのインストール
pip install -r requirements.txt

# exeファイル化
pyinstaller --onefile -n SearchPDF search_pdf.py
```

## 使用方法

### 基本構文

```bash
python search_pdf.py <PDFファイル|ディレクトリ> -s <検索文字列> [オプション]
python search_pdf.py <PDFファイル|ディレクトリ> -f <検索文字列リストファイル> [オプション]
```

### オプション

| オプション | 説明 |
|-----------|------|
| `-s, --search-string` | 検索文字列（単一） |
| `-f, --search-file` | 検索文字列リストファイル（改行区切り） |
| `-i, --ignore-case` | 大文字・小文字を区別しない |
| `-v, --verbose` | 詳細出力（ブックマーク、ページ、ヒット箇所の文章） |
| `-o, --output` | 出力ファイル（省略時は標準出力） |
| `-e, --encoding` | 出力エンコーディング（-oあり時のデフォルト: shift_jis、標準出力時: utf-8） |

### 使用例

**単一ファイルを検索:**
```bash
python search_pdf.py document.pdf -s "検索ワード"
```

**ディレクトリ内を再帰検索:**
```bash
python search_pdf.py ./pdfs -s "検索ワード"
```

**複数の検索ワードをファイルで指定:**
```bash
python search_pdf.py ./pdfs -f search_words.txt
```

**大文字・小文字を区別せず検索:**
```bash
python search_pdf.py document.pdf -s "keyword" -i
```

**詳細情報付きで結果をファイル出力:**
```bash
python search_pdf.py ./pdfs -s "検索ワード" -v -o result.csv
```

## 出力形式

### 基本出力（CSV）

```csv
"検索文字列","ファイル名"
"検索ワード","subdir/document.pdf"
```

### 詳細出力（-v オプション）

```csv
"検索文字列","ファイル名","ブックマーク","ページ","ヒット箇所"
"検索ワード","subdir/document.pdf","第1章 はじめに","5","この文章には検索ワードが含まれています。"
```

## 検索文字列リストファイルの形式

改行区切りで検索文字列を記述します：

```
キーワード1
キーワード2
キーワード3
```

空行は無視されます。
