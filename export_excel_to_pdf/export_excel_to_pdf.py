import sys
import tempfile
import time
from pathlib import Path

import xlwings as xw  # type: ignore
from plyer import notification  # type: ignore
from PyPDF2 import PdfMerger  # type: ignore


def export_excels_to_pdf(input_dir, output_dir=None, recursive=False, add_bookmarks: bool = False):
    start_time = time.time()
    input_path = Path(input_dir).resolve()
    if not input_path.is_dir() and not input_path.is_file():
        raise ValueError(f"指定されたパスが存在しません: {input_path}")

    output_path = Path(output_dir).resolve() if output_dir else input_path
    if output_path.is_file():
        output_path = output_path.parent
    output_path.mkdir(parents=True, exist_ok=True)

    # input_pathがファイルの場合、そのファイルのみ処理
    if input_path.is_file():
        excel_files = [input_path]
        input_path = input_path.parent
    else:
        # 対象ファイル一覧（再帰オプションあり）
        pattern = "**/*.xls*" if recursive else "*.xls*"
        excel_files = sorted(list(input_path.glob(pattern)))
        # 一時ファイルを除外
        excel_files = [f for f in excel_files if not f.name.startswith("~$")]
    total = len(excel_files)
    if total == 0:
        print("対象となるExcelファイルが見つかりません。")
        return

    failed = []

    print("=== 一括PDF変換開始 ===")
    print(f"対象フォルダ: {input_path}")
    print(f"出力先フォルダ: {output_path}")
    print(f"対象ファイル数: {total}")
    print("----------------------------")

    # Excelバックグラウンドインスタンス
    app = xw.App(visible=False, add_book=False)
    app.display_alerts = False
    app.screen_updating = False

    try:
        for i, file in enumerate(excel_files, start=1):
            # 出力先の相対パス構造を維持
            rel_path = file.relative_to(input_path).with_suffix(".pdf")
            pdf_path = output_path / rel_path
            pdf_path.parent.mkdir(parents=True, exist_ok=True)

            # ExcelファイルよりもPDFファイルが新しい場合はスキップ
            if pdf_path.exists() and pdf_path.stat().st_mtime >= file.stat().st_mtime:
                print(f"[{i}/{total}] スキップ: {file} （PDFの方が新しい）")
                continue

            print(f"[{i}/{total}] 変換中: {file} → {pdf_path.name}")

            try:
                if add_bookmarks:
                    with tempfile.TemporaryDirectory() as tmpdir_str:
                        tmpdir_path = Path(tmpdir_str)
                        book = app.books.open(file)
                        merger = PdfMerger()

                        try:
                            for sheet in book.sheets:
                                # xlSheetVisible = -1
                                if sheet.api.Visible != -1:
                                    continue  # 非表示シートはスキップ

                                tmp_pdf = tmpdir_path / f"{sheet.name}.pdf"
                                # 各シートを一時PDFとして保存
                                sheet.api.ExportAsFixedFormat(0, str(tmp_pdf))
                                # PyPDF2で追加＋ブックマーク
                                merger.append(str(tmp_pdf), outline_item=sheet.name)

                            if merger.pages:
                                merger.write(pdf_path)
                            else:
                                print("  → 変換スキップ（全シート非表示）")

                        finally:
                            merger.close()
                            book.close()

                else:
                    book = app.books.open(file)
                    try:
                        book.to_pdf(path=pdf_path)
                    finally:
                        book.close()

            except Exception as e:
                print(f"  ❌ 変換失敗: {file.name} ({e})")
                failed.append(str(file))
        print("\n=== 一括PDF変換完了 ===")

    finally:
        # Excelプロセスを確実に終了
        try:
            app.quit()
            del app
        except Exception:
            pass

    # 処理時間
    elapsed = time.time() - start_time
    print(f"処理時間: {elapsed:.1f} 秒")

    # サマリ出力
    success_count = total - len(failed)
    print(f"✅ 成功: {success_count} 件")
    print(f"❌ 失敗: {len(failed)} 件")

    if failed:
        print("\n▼ 変換失敗ファイル一覧:")
        for f in failed:
            print(f"  - {f}")

    # 通知
    notification.notify(
        title="Excel → PDF 一括変換",
        message=f"完了: 成功 {success_count} / 失敗 {len(failed)}\n処理時間: {elapsed:.1f} 秒",
        timeout=5,
        app_name="export_excel_to_pdf",
    )


def print_usage():
    print("使い方: python export_excel_to_pdf.py <入力フォルダ> [-o <出力フォルダ>] [-r] [-b]")
    print("  -o: 出力フォルダ（省略時は入力フォルダと同じ）")
    print("  -nr: サブフォルダも再帰的に処理しない（省略時はする）")
    print("  -nb: 各シートをブックマーク付きでPDFに結合しない（省略時はする）")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        # ユーザ入力を待つ
        input("Enterキーを押して終了...")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = None
    recursive = True
    add_bookmarks = True

    for arg in sys.argv[2:]:
        if arg == "-nr":
            recursive = False
        elif arg == "-nb":
            add_bookmarks = False
        elif arg == "-o":
            if sys.argv.index(arg) + 1 < len(sys.argv):
                output_dir = sys.argv[sys.argv.index(arg) + 1]

    export_excels_to_pdf(input_dir, output_dir, recursive, add_bookmarks)
