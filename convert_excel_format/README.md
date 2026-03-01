# Excelフォーマット一括修正ツール

複数のExcelファイルのフォーマット・値を一括で修正・編集するためのPythonスクリプトです。
Pythonと `xlwings` を利用し、マクロに代わって複雑な要件へ柔軟に対応できる土台（基盤クラス `ExcelEditor`）を提供しています。

## 動作環境・前提条件

- OS: Windows または macOS (Excelアプリケーションがインストールされていること)
- Python 3.7+
- ライブラリ: `xlwings`
  - インストールコマンド: `pip install xlwings`

## ディレクトリ構成（例）

```
convert_excel_format/
├── convert_excel_format.py (本スクリプト)
├── README.md               (本ドキュメント)
├── template.xlsx           (データや図形、書式のコピー元となるテンプレートファイル)
└── excel_files/            (処理対象のExcel群を格納するフォルダ)
    ├── 対象_01.xlsx
    └── 対象_02.xlsx
```

## 使い方

1. `convert_excel_format.py` ファイルの先頭にある「設定」部分を環境に合わせて変更してください。
    - `TARGET_DIR`: 対象ファイルがあるフォルダ
    - `TEMPLATE_FILE`: コピー元に使うファイル
2. ターミナルからスクリプトを実行します。
    ```bash
    python convert_excel_format.py
    ```
    実行時に `--target-dir` (または `-t`) オプションで対象フォルダを、`--backup-dir` (または `-b`) オプションでバックアップフォルダを指定することも可能です（設定内の値よりも優先されます）。
    また、`--debug` (または `-d`) オプションを指定すると、編集操作の内容が標準出力にデバッグログとして出力されます。
    ```bash
    python convert_excel_format.py -t ./another_excel_files -b ./my_backup -d
    ```

## カスタマイズ方法 (`ExcelEditor` クラス)

このスクリプトは、Excelの操作をラップした `ExcelEditor` クラスを持っています。
これを利用することで、`main()` 関数内で直感的に以下のような操作が行えます。

### 利用できる主な機能

| やりたいこと | メソッド・関数 例 |
|---|---|
| 対象シートの抽出 | `get_target_sheets(wb, SHEET_PATTERN)` (正規表現で指定) |
| 行/列の検索 | `editor.find_row_by_keyword(col, keyword)`<br>`editor.find_col_by_keyword(row, keyword)` |
| 列レターのオフセット移動 | `get_col_by_offset("D", -1)` → "C" を返す |
| セル範囲アドレスの取得 | `get_range_address("A1", 2, 3)` → "A1:C2" を返す |
| 範囲の取得 | `editor.get_range("A2:D3")` |
| 値の設定 | `editor.set_value("D5", "更新済み")` |
| フォントの設定 | `editor.set_font_size(範囲, サイズ)`<br>`editor.set_font_name(範囲, フォント名)` |
| 背景色の設定 | `editor.set_background_color(範囲, (R, G, B))` (例: 黄色は `(255, 255, 0)`) |
| 罫線の設定 | `editor.set_borders(範囲)` |
| 配置（アライン）の設定 | `editor.set_alignment(範囲, horizontal=xlHAlignCenter)` |
| テキストの折り返し・縮小 | `editor.set_text_control(範囲, wrap_text=True)` など |
| セルの結合 | `editor.set_merge("A1:B2", merge=True)` |
| 表示形式の変更 | `editor.set_number_format("A1", "@")` (文字列化) など |
| 行・列の削除 | `editor.delete_rows(開始行, 終了行)`<br>`editor.delete_cols(開始列, 終了列)` |
| セル範囲の削除（シフト） | `editor.delete_range("A1:B2", shift_up=True)` |
| セル範囲の挿入（シフト） | `editor.insert_range("A1:B2", shift_down=True)` |
| ページ設定（印刷設定） | `editor.set_page_setup(orientation=xlLandscape, fit_width=1)` |
| 印刷範囲の設定 | `editor.set_print_area("A1:G50")` |
| テンプレートからのコピー挿入 | `editor.insert_copied_rows(sh_template, "1:3", dest_row=5)` |
| 図形（シェイプ）のコピー | `editor.paste_shape(sh_template, "ShapeName", "D5")` |
| テキストによる図形削除 | `editor.delete_shapes_by_text("削除対象の文字")` |

処理のサンプルは `convert_excel_format.py` の `main()` 関数内に記述されています。
自身の目的に応じて処理の順序や内容を書き換えてご利用ください。

## 注意事項
- 実行中は Excel のウィンドウが開いて自動で動きます。バックグラウンドで動かしたい場合は `xw.App(visible=False)` に変更してください。
- ターミナルの文字化けを防ぐため、Windows環境ではソースコード内で自動的に `chcp 65001` が実行されます。
- 万が一途中でエラーが起きた場合でも、ファイルは保存して閉じるように設計されています。
