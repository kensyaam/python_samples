import pathlib
import re

import xlwings as xw

# ==========================================
# 1. 設定（ご自身の環境に合わせて変更してください）
# ==========================================
TARGET_DIR = "./excel_files"  # 対象のExcelファイル群があるフォルダ
TEMPLATE_FILE = "./template.xlsx"  # 作業用に用意したコピー元Excel
TEMPLATE_SHEET = "コピー元"  # コピー元シート名
COPY_ROWS = "1:3"  # コピーする行（例：1〜3行目）

SHEET_PATTERN = r"^対象_.*"  # 対象シート名の規則（正規表現。例：「対象_」で始まる）
SEARCH_COL = "B"  # 検索対象の列
SEARCH_KEYWORD = "挿入位置"  # 検索するキーワード
DELETE_ROW_COUNT = 2  # 起点から削除する行数

TARGET_CELL = "D5"  # 値を変更するセル
NEW_VALUE = "更新済み"  # 変更後の値
# ==========================================


def main():
    # Excelアプリケーションを起動（visible=Trueにすると動いている様子が見えます）
    # 完全に裏で動かしたい場合は visible=False に変更してください。
    app = xw.App(visible=True, add_book=False)

    try:
        # コピー元のテンプレートファイルを開き、コピー範囲をセット
        wb_template = app.books.open(TEMPLATE_FILE)
        sh_template = wb_template.sheets[TEMPLATE_SHEET]
        rng_copy = sh_template.range(COPY_ROWS)

        # 指定ディレクトリ内の .xlsx ファイルを全て取得
        target_dir_path = pathlib.Path(TARGET_DIR)
        excel_files = target_dir_path.glob("*.xlsx")

        for file_path in excel_files:
            # テンプレートファイル自身が同じフォルダにある場合はスキップ
            if file_path.name == pathlib.Path(TEMPLATE_FILE).name:
                continue

            print(f"処理開始: {file_path.name}")
            wb = app.books.open(file_path)

            try:
                # ブック内の全シートをループ確認
                for sheet in wb.sheets:
                    # シート名が規則（正規表現）に合致するか判定
                    if re.match(SHEET_PATTERN, sheet.name):
                        print(f"  シート処理中: {sheet.name}")

                        # 指定列（例: B1〜B1000）の値をリストとして取得し、キーワードを検索
                        # ※検索範囲はデータの量に合わせて広げてください
                        search_range = sheet.range(
                            f"{SEARCH_COL}1:{SEARCH_COL}1000"
                        ).value
                        target_row = None

                        if search_range:
                            for i, val in enumerate(search_range):
                                if val == SEARCH_KEYWORD:
                                    target_row = (
                                        i + 1
                                    )  # Excelの行番号は1から始まるため +1
                                    break

                        if target_row:
                            # --- 1. 指定行数の削除 ---
                            # .api.Delete() を使うことでExcelの標準機能として行を削除します
                            sheet.range(
                                f"{target_row}:{target_row + DELETE_ROW_COUNT - 1}"
                            ).api.Delete()

                            # --- 2. 書式を含めた行のコピーと挿入 ---
                            rng_copy.api.Copy()  # クリップボードに書式ごとコピー

                            # Shift=-4121 は「下方向にシフト (xlDown)」を意味するExcelの内部定数
                            sheet.range(f"{target_row}:{target_row}").api.Insert(
                                Shift=-4121
                            )

                            # コピーモードを解除（ExcelでEscキーを押すのと同じ動作）
                            app.api.CutCopyMode = False

                            # --- 3. 指定セルの値変更 ---
                            sheet.range(TARGET_CELL).value = NEW_VALUE
                        else:
                            print(
                                f"    キーワード '{SEARCH_KEYWORD}' が見つかりませんでした。"
                            )

            finally:
                # エラーが起きても対象ファイルは必ず保存して閉じる
                wb.save()
                wb.close()

    finally:
        # すべての処理が終わったらテンプレートを閉じ、Excelアプリ自体を終了する
        if "wb_template" in locals():
            wb_template.close()
        app.quit()
        print("すべての処理が完了しました。")


if __name__ == "__main__":
    main()
