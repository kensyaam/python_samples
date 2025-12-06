# Excel一括PDF変換ツール

指定フォルダ配下のExcelファイルを、一括でPDFに変換します。  
サブフォルダ再帰処理にも対応しています。

<!-- @import "[TOC]" {cmd="toc" depthFrom=2 depthTo=4 orderedList=false} -->

<!-- code_chunk_output -->

- [環境構築手順](#環境構築手順)
  - [1. 仮想環境を作成](#1-仮想環境を作成)
  - [2. 仮想環境を有効化](#2-仮想環境を有効化)
  - [3. 依存パッケージのインストール](#3-依存パッケージのインストール)
  - [4. exeファイル化 (ExcelToPDF)](#4-exeファイル化-exceltopdf)
- [実行方法](#実行方法)
  - [Python](#python)
    - [ラッパー (内部で仮想環境の有効化)](#ラッパー-内部で仮想環境の有効化)
  - [ExcelToPDF.exe](#exceltopdfexe)
    - [ヘルパー (入力フォルダ固定)](#ヘルパー-入力フォルダ固定)

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

### 4. exeファイル化 (ExcelToPDF)

```bash
python -c "from PIL import Image; Image.open('app.png').resize((256,256), Image.LANCZOS).save('app.ico')"
pyinstaller --hidden-import=plyer.platforms.win.notification --onefile --icon=app.ico -n ExcelToPDF export_excel_to_pdf.py 
```

## 実行方法

### Python

```bash
python export_excel_to_pdf.py <入力フォルダ> [-o <出力フォルダ>] [-nr] [-nb]
  -o: 出力フォルダ（省略時は入力フォルダと同じ）
  -nr: サブフォルダも再帰的に処理しない（省略時はする）
  -nb: 各シートをブックマーク付きでPDFに結合しない（省略時はする）
```

#### ラッパー (内部で仮想環境の有効化)

##### バッチファイル

```bat
export_excel_to_pdf_w.bat <入力フォルダ> [-o <出力フォルダ>] [-nr] [-nb]
```

##### シェルスクリプト (Git for windows)

```bash
./export_excel_to_pdf_w.sh <入力フォルダ> [-o <出力フォルダ>] [-nr] [-nb]
```

### ExcelToPDF.exe

```bat
ExcelToPDF.exe <入力フォルダ> [-o <出力フォルダ>] [-nr] [-nb]
```

#### ヘルパー (入力フォルダ固定)

```bat
ExcelToPDFW.bat [-o <出力フォルダ>] [-nr] [-nb]
```

入力フォルダはbatファイル内の変数に設定
