"""
Excel ブック内のセルとシェイプのフォントを一括変更するスクリプト

要件:
- xlwings を使用してExcelの書式を参照・編集
- UI操作をブロックしない
- フォルダまたはファイルパスを引数で指定
- メイリオ以外のフォントをメイリオに変更し、サイズを0.9倍に調整
- 非表示シート・セル・シェイプは対象外
- 値が入っているセルのみを処理
"""

import argparse
import math
import time
import traceback
from pathlib import Path
from typing import Any, Set, cast

import xlwings as xw  # type: ignore
from xlwings import Range, Shape, Sheet


class ExcelFontChanger:
    """Excelファイルのフォントを変更するクラス"""

    TARGET_FONT = "メイリオ"
    FONT_SIZE_RATIO_FOR_GE_11 = 0.9
    FONT_SIZE_RATIO_FOR_LT_11 = 0.85
    LINE_SPACE_WITHIN = 0.8

    def __init__(self, exclude_sheets=None):
        """
        Args:
            exclude_sheets (list): 処理対象外のシート名リスト
        """
        self.exclude_sheets = exclude_sheets or []

    def process_path(self, path):
        """パス(ファイルまたはフォルダ)を処理"""
        path_obj = Path(path)

        if not path_obj.exists():
            print(f"エラー: パスが存在しません: {path}")
            return

        if path_obj.is_file():
            if path_obj.suffix.lower() in [".xlsx", ".xlsm", ".xls"]:
                self.process_file(str(path_obj))
            else:
                print(f"スキップ: Excelファイルではありません: {path}")
        elif path_obj.is_dir():
            excel_files = (
                list(path_obj.glob("*.xlsx")) + list(path_obj.glob("*.xlsm")) + list(path_obj.glob("*.xls"))
            )

            print(f"フォルダ内のExcelファイル数: {len(excel_files)}")

            for i, file_path in enumerate(excel_files, 1):
                print(f"\n[{i}/{len(excel_files)}] {file_path.name}")
                self.process_file(str(file_path))

    def process_file(self, file_path: Path):
        """単一のExcelファイルを処理"""
        print(f"処理開始: {file_path}")

        try:
            # screen_updating=False でUI操作をブロックしない
            app = xw.App(visible=False, add_book=False)
            app.screen_updating = False
            app.display_alerts = False

            wb = app.books.open(file_path)

            try:
                visible_sheets = [ws for ws in wb.sheets if ws.visible]
                target_sheets = [ws for ws in visible_sheets if ws.name not in self.exclude_sheets]

                print(f"  対象シート数: {len(target_sheets)}/{len(wb.sheets)}")

                for i, sheet in enumerate(target_sheets, 1):
                    sheet = cast(Sheet, sheet)
                    print(f"  [{i}/{len(target_sheets)}] シート: {sheet.name}")
                    self.process_sheet(sheet)

                wb.save()
                print("  ✓ 保存完了")

            finally:
                wb.close()
                app.quit()

        except Exception as e:
            print(f"  ✗ エラー: {e}")
            traceback.print_exc()

    def process_sheet(self, sheet: Sheet):
        """シート内のセルとシェイプを処理"""
        # セルの処理
        cell_count = self.process_cells(sheet)
        print(f"    - セル処理完了: {cell_count}個")

        # シェイプの処理
        shape_count = self.process_shapes(sheet)
        print(f"    - シェイプ処理完了: {shape_count}個")

    def process_cells(self, sheet: Sheet):
        """セルのフォントを処理"""
        changed_count = 0
        processed_addresses: Set[Any] = set()  # 重複処理を避けるためのセット

        try:
            # 1. SpecialCells で値が入っているセルを取得
            # xlCellTypeConstants(2) = 定数(文字列・数値)
            # xlCellTypeFormulas(-4123) = 数式
            constants = None
            formulas = None

            try:
                constants = sheet.api.Cells.SpecialCells(2)  # xlCellTypeConstants
            except Exception:
                pass

            try:
                formulas = sheet.api.Cells.SpecialCells(-4123)  # xlCellTypeFormulas
            except Exception:
                pass

            # 定数セルの処理
            if constants is not None:
                changed_count += self._process_range(sheet, constants, processed_addresses)

            # 数式セルの処理
            if formulas is not None:
                changed_count += self._process_range(sheet, formulas, processed_addresses)

            # 2. 結合セルを取得して処理
            # UsedRange から結合セルを抽出
            try:
                used_range = sheet.api.UsedRange
                # if used_range is not None:
                if False:
                    # UsedRange内の全セルをチェック（結合セルを探す）
                    for cell_api in used_range:
                        try:
                            # 結合セルかチェック
                            if not cell_api.MergeCells:
                                continue

                            print(f"      - 結合セル発見: {cell_api.Address}")

                            # 結合エリアの左上セル（代表セル）かチェック
                            merge_area = cell_api.MergeArea
                            if cell_api.Row != merge_area.Row or cell_api.Column != merge_area.Column:
                                continue

                            print(f"        - 代表セル: {cell_api.Address}")

                            # アドレスを取得
                            addr = cell_api.Address
                            if addr in processed_addresses:
                                continue
                                # pass

                            # xlwings のセルオブジェクトに変換
                            xw_cell = sheet.range(addr)

                            # 値がない場合はスキップ
                            if xw_cell.value is None:
                                continue

                            # 非表示セルはスキップ
                            if cell_api.EntireRow.Hidden or cell_api.EntireColumn.Hidden:
                                continue

                            # フォント処理
                            print(f"        - フォント処理: {addr}")
                            if self._process_single_cell(xw_cell):
                                changed_count += 1

                            processed_addresses.add(addr)

                        except Exception as e:
                            print(f"        警告: 結合セル処理中にエラー: {e}")
                            # pass
            except Exception:
                pass

        except Exception as e:
            print(f"    警告: セル処理中にエラー: {e}")

        return changed_count

    def _process_range(self, sheet: Sheet, range_obj, processed_addresses: Set):
        """Range オブジェクト内のセルを処理"""
        changed_count = 0

        try:
            # Range を xlwings の Range に変換
            for area in range_obj.Areas:
                xw_range = sheet.range(area.Address)

                for cell in xw_range:
                    # 既に処理済みの場合はスキップ
                    if cell.address in processed_addresses:
                        continue

                    # 非表示セルはスキップ
                    try:
                        if cell.api.EntireRow.Hidden or cell.api.EntireColumn.Hidden:
                            continue
                    except Exception:
                        continue

                    # フォント処理
                    if self._process_single_cell(cell):
                        changed_count += 1

                    processed_addresses.add(cell.address)

        except Exception:
            pass

        return changed_count

    def _process_single_cell(self, cell: Range):
        """単一セルのフォントを処理"""
        try:
            font = cell.font
            if font.name != self.TARGET_FONT:
                # print(f"        - フォント: {cell.address} - {font.name}, {font.size}")
                old_name = font.name
                old_size = font.size
                old_bold = font.bold

                # font.size が None の場合（リッチテキストなど）は
                # デフォルトサイズ（11pt）を使用
                if old_size is None:
                    try:
                        # Characters(1, 1) で最初の1文字を取得
                        old_size = cell.api.Characters(1, 1).Font.Size
                        old_bold = cell.api.Characters(1, 1).Font.Bold
                    except Exception:
                        # それでも取得できない場合はデフォルト（11pt）を使用
                        old_size = 11
                    print(f"                  : old_size: None → {old_size}")

                # new_size = math.floor(old_size * self.FONT_SIZE_RATIO)
                if old_size >= 11:
                    new_size = (
                        math.floor(old_size * self.FONT_SIZE_RATIO_FOR_GE_11 * 2) / 2
                    )  # 0.5刻みで小さい方に丸める
                else:
                    new_size = (
                        math.floor(old_size * self.FONT_SIZE_RATIO_FOR_LT_11 * 2) / 2
                    )  # 0.5刻みで小さい方に丸める

                font.name = self.TARGET_FONT
                font.size = new_size
                font.bold = old_bold
                print(
                    f"        - フォント: {cell.address} - [{old_name}, {old_size}]"
                    f" -> {font.name}, {font.size} : {repr(cell.value)}"
                )
                return True

        except Exception as e:
            print(f"        警告: セルフォント処理中にエラー: {e}")
            pass

        return False

    def process_shapes(self, sheet: Sheet):
        """シェイプのフォントを処理"""
        changed_count = 0

        try:
            shapes = sheet.shapes

            for shape in shapes:
                try:
                    # 非表示シェイプはスキップ
                    if not shape.api.Visible:
                        continue

                    # グループシェイプの場合は再帰的に処理
                    if self._is_group_shape(shape):
                        changed_count += self._process_grouped_shapes(shape)
                    else:
                        # TextFrame2 を優先的に使用
                        if self.has_textframe2(shape):
                            if self.process_shape_textframe2(shape):
                                changed_count += 1
                        # TextFrame2 がない場合は TextFrame を使用
                        elif self.has_textframe(shape):
                            if self.process_shape_textframe(shape):
                                changed_count += 1

                except Exception:
                    # 個別シェイプのエラーは無視して続行
                    pass

        except Exception as e:
            print(f"    警告: シェイプ処理中にエラー: {e}")

        return changed_count

    def has_textframe2(self, shape: Shape):
        return self.has_textframe2_com(shape.api)

    def has_textframe2_com(self, com_shape):
        """シェイプが TextFrame2 を持つか確認"""
        try:
            return com_shape.TextFrame2.HasText
        except Exception:
            return False

    def has_textframe(self, shape: Shape):
        return self.has_textframe_com(shape.api)

    def has_textframe_com(self, com_shape):
        """シェイプが TextFrame を持つか確認"""
        try:
            return hasattr(com_shape, "TextFrame") and com_shape.api.TextFrame.Characters().Text != ""
        except Exception:
            return False

    def _is_group_shape(self, shape: Shape):
        """シェイプがグループシェイプか確認"""
        try:
            # Type = 6 が msoGroup
            return shape.api.Type == 6
        except Exception:
            return False

    def _process_grouped_shapes(self, group_shape: Shape):
        return self._process_grouped_com_shapes(group_shape.api)

    def _process_grouped_com_shapes(self, com_group_shape):
        """グループシェイプ内のシェイプを再帰的に処理"""
        changed_count = 0

        try:
            # GroupItems で グループ内のシェイプを取得
            group_items = com_group_shape.GroupItems

            for i in range(1, group_items.Count + 1):
                try:
                    com_shape = group_items.Item(i)

                    # 非表示はスキップ
                    if not com_shape.Visible:
                        continue

                    # さらにグループシェイプの場合は再帰処理
                    if com_shape.Type == 6:
                        changed_count += self._process_grouped_com_shapes(com_shape)
                    else:
                        # TextFrame2 を優先的に使用
                        if self.has_textframe2_com(com_shape):
                            if self.process_shape_textframe2_com(com_shape):
                                changed_count += 1
                        # TextFrame2 がない場合は TextFrame を使用
                        elif self.has_textframe_com(com_shape):
                            if self.process_shape_textframe_com(com_shape):
                                changed_count += 1
                except Exception as e:
                    print(f"  ✗ エラー: {e}")
                    traceback.print_exc()

        except Exception as e:
            print(f"  ✗ エラー: {e}")
            traceback.print_exc()

        return changed_count

    def process_shape_textframe2(self, shape: Shape):
        return self.process_shape_textframe2_com(shape.api)

    def process_shape_textframe2_com(self, com_shape):
        """TextFrame2 を使用してシェイプのフォントを処理"""
        try:
            text_frame = com_shape.TextFrame2.TextRange
            font = text_frame.Font

            if font.Name != self.TARGET_FONT:
                old_name = font.Name
                old_size = font.Size

                # new_size = math.floor(old_size * self.FONT_SIZE_RATIO)
                if old_size >= 11:
                    new_size = (
                        math.floor(old_size * self.FONT_SIZE_RATIO_FOR_GE_11 * 2) / 2
                    )  # 0.5刻みで小さい方に丸める
                else:
                    new_size = (
                        math.floor(old_size * self.FONT_SIZE_RATIO_FOR_LT_11 * 2) / 2
                    )  # 0.5刻みで小さい方に丸める

                font.Name = self.TARGET_FONT
                font.NameFarEast = self.TARGET_FONT
                font.Size = new_size
                print(
                    f"        - フォント: [{com_shape.Name}, {com_shape.ID}] - [{old_name}, {old_size}]"
                    f" -> {font.Name}, {font.Size} : {repr(text_frame.Text)}"
                )

                self._adjust_shape_line_spacing_com(com_shape)
                return True

        except Exception:
            pass

        return False

    def process_shape_textframe(self, shape: Shape):
        """TextFrame を使用してシェイプのフォントを処理"""
        try:
            characters = shape.api.TextFrame.Characters()
            font = characters.Font

            if font.Name != self.TARGET_FONT:
                old_size = font.Size
                # new_size = math.floor(old_size * self.FONT_SIZE_RATIO)
                if old_size >= 11:
                    new_size = (
                        math.floor(old_size * self.FONT_SIZE_RATIO_FOR_GE_11 * 2) / 2
                    )  # 0.5刻みで小さい方に丸める
                else:
                    new_size = (
                        math.floor(old_size * self.FONT_SIZE_RATIO_FOR_LT_11 * 2) / 2
                    )  # 0.5刻みで小さい方に丸める

                font.Name = self.TARGET_FONT
                font.NameFarEast = self.TARGET_FONT
                font.Size = new_size

                # self._adjust_shape_line_spacing(shape)
                return True

        except Exception:
            pass

        return False

    def _adjust_shape_line_spacing_com(self, com_shape):
        """シェイプの行間を倍数 0.8 に設定（TextFrame2）"""
        try:
            # see.
            # https://learn.microsoft.com/ja-jp/office/vba/api/office.textrange2.paragraphformat
            # https://learn.microsoft.com/ja-jp/office/vba/api/overview/library-reference/paragraphformat2-members-office
            para_format = com_shape.TextFrame2.TextRange.ParagraphFormat
            # 行間を行数で指定
            para_format.LineRuleWithin = 1  # msoTrue
            para_format.SpaceWithin = self.LINE_SPACE_WITHIN
        except Exception as e:
            print(f"  ✗ エラー: {e}")
            traceback.print_exc()


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="Excelファイルのフォントを一括変更します")
    parser.add_argument("path", help="処理対象のExcelファイルまたはフォルダのパス", default="./work/excel")
    parser.add_argument(
        "--exclude-sheets",
        nargs="+",
        default=[],
        help="処理対象外のシート名(スペース区切りで複数指定可)",
    )

    args = parser.parse_args()

    start_time = time.time()

    print("=" * 60)
    print("Excel フォント一括変更ツール")
    print("=" * 60)
    print(f"対象パス: {args.path}")
    if args.exclude_sheets:
        print(f"除外シート: {', '.join(args.exclude_sheets)}")
    print("変更内容: メイリオ以外 → メイリオ (サイズ × 0.84)")
    print("=" * 60)
    print()

    changer = ExcelFontChanger(exclude_sheets=args.exclude_sheets)
    changer.process_path(args.path)

    elapsed = time.time() - start_time

    print()
    print("=" * 60)
    print(f"処理完了: {elapsed:.1f} 秒")
    print("=" * 60)


if __name__ == "__main__":
    main()
