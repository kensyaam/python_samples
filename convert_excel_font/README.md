
# Excel一括フォント変換ツール

指定Excelファイル、もしくは、指定フォルダ配下のExcelファイルを、一括でPDFに変換します。  

<!-- @import "[TOC]" {cmd="toc" depthFrom=2 depthTo=6 orderedList=false} -->

<!-- code_chunk_output -->

- [環境構築手順](#環境構築手順)
  - [1. 仮想環境を作成](#1-仮想環境を作成)
  - [2. 仮想環境を有効化](#2-仮想環境を有効化)
  - [3. 依存パッケージのインストール](#3-依存パッケージのインストール)
- [実行方法](#実行方法)
  - [ラッパー (内部で仮想環境の有効化)](#ラッパー-内部で仮想環境の有効化)
    - [バッチファイル](#バッチファイル)
    - [シェルスクリプト (Git for windows)](#シェルスクリプト-git-for-windows)

<!-- /code_chunk_output -->

---

## 環境構築手順

### 1. 仮想環境を作成

```bash
python -m venv .venv
```

### 2. 仮想環境を有効化

```bash
# Cmd
.venv\Scripts\activate

# bash (Git for windows)
source .venv/Scripts/activate
```

### 3. 依存パッケージのインストール

```bash
pip install -r requirements.txt

# 開発用
pip install -r requirements-dev.txt
```

## 実行方法

```bash
python convert_excel_font.py <target_path> [--exclude-sheets <exclude_sheets>]
  <target_path>: 処理対象のExcelファイル／フォルダのパス（デフォルト：./work/excel）
  --exclude-sheets: 処理対象外のシート名(スペース区切りで複数指定可) （省略時は無し）
```

### ラッパー (内部で仮想環境の有効化)

#### バッチファイル

```bat
convert_excel_font_w.bat <target_path> [--exclude-sheets <exclude_sheets>]
```

#### シェルスクリプト (Git for windows)

```bash
./convert_excel_font_w.sh <target_path> [--exclude-sheets <exclude_sheets>]
```
