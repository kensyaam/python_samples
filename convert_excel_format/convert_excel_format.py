import argparse
import os
import pathlib
import re
import shutil
from typing import Any, List, Optional, Tuple

import xlwings as xw  # type: ignore

# ==========================================
# 1. 設定（ご自身の環境に合わせて変更してください）
# ==========================================
TARGET_DIR = "./excel_files"  # 対象のExcelファイル群があるフォルダ
BACKUP_DIR = "./backup"  # 変更前のファイルを退避するフォルダ
TEMPLATE_FILE = "./template.xlsx"  # 作業用に用意したコピー元Excel
TEMPLATE_SHEET = "コピー元"  # コピー元シート名

# ==========================================
# Excel API 定数
# ==========================================
# --- セル・範囲の挿入・削除や移動方向に関する定数 ---
xlDown = -4121  # 下方向へシフト
xlToRight = -4161  # 右方向へシフト
xlToLeft = -4159  # 左方向へシフト
xlUp = -4162  # 上方向へシフト

# --- 罫線の位置に関する定数 ---
xlEdgeLeft = 7  # セル/範囲の左辺
xlEdgeTop = 8  # セル/範囲の上辺
xlEdgeBottom = 9  # セル/範囲の下辺
xlEdgeRight = 10  # セル/範囲の右辺
xlInsideVertical = 11  # 範囲内の垂直な内側罫線
xlInsideHorizontal = 12  # 範囲内の水平な内側罫線

# --- 罫線の種類 (LineStyle) に関する定数 ---
xlContinuous = 1  # 実線
xlDash = -4115  # 破線
xlDashDot = 4  # 一点鎖線
xlDashDotDot = 5  # 二点鎖線
xlDot = -4118  # 点線
xlDouble = -4119  # 二重線
xlSlantDashDot = 13  # 斜め一点鎖線
xlLineStyleNone = -4142  # 罫線なし

# --- 罫線の太さ (Weight) に関する定数 ---
xlHairline = 1  # 極細線 (ヘアライン)
xlThin = 2  # 細線 (デフォルト値)
xlMedium = -4138  # 中太線
xlThick = 4  # 太線

# --- セルの配置（アラインメント）に関する定数 ---
xlHAlignCenter = -4108  # (水平)中央揃え
xlVAlignCenter = -4108  # (垂直)中央揃え
xlHAlignLeft = -4131  # (水平)左揃え
xlHAlignRight = -4152  # (水平)右揃え
xlVAlignBottom = -4107  # (垂直)下揃え
xlVAlignTop = -4160  # (垂直)上揃え

# --- ページ設定に関する定数 ---
xlLandscape = 2  # 横向き
xlPortrait = 1  # 縦向き
# ==========================================


def col_num_to_letter(col_num: int) -> str:
    """列番号を列レター(A, B, ..., Z, AA...)に変換する"""
    string = ""
    while col_num > 0:
        col_num, remainder = divmod(col_num - 1, 26)
        string = chr(65 + remainder) + string
    return string


def col_letter_to_num(col_letter: str) -> int:
    """列レターを列番号に変換する"""
    num = 0
    for c in col_letter.upper():
        if ord("A") <= ord(c) <= ord("Z"):
            num = num * 26 + (ord(c) - ord("A") + 1)
    return num


def get_col_by_offset(base_col: str, offset: int) -> str:
    """基準列から指定したオフセット分移動した列レターを取得する（基準列=D, offset=-1なら C を返す）"""
    base_num = col_letter_to_num(base_col)
    new_num = base_num + offset
    if new_num < 1:
        raise ValueError("オフセット後の列番号が1未満になります。")
    return col_num_to_letter(new_num)


def get_range_address(base_cell: str, row_count: int, col_count: int) -> str:
    """基準セルから指定した行数・列数分の範囲アドレスを取得する

    Args:
        base_cell (str): 基準となるセル（例: "A1"）
        row_count (int): 範囲に含める行数
        col_count (int): 範囲に含める列数

    Returns:
        str: 範囲アドレス（例: "A1:C2"）
    """
    match = re.match(r"([A-Za-z]+)(\d+)", base_cell)
    if not match:
        raise ValueError(f"無効なセルアドレスです: {base_cell}")

    start_col_letter, start_row_str = match.groups()
    start_row = int(start_row_str)

    end_row = start_row + row_count - 1

    start_col_num = col_letter_to_num(start_col_letter)
    end_col_num = start_col_num + col_count - 1
    end_col_letter = col_num_to_letter(end_col_num)

    return f"{base_cell}:{end_col_letter}{end_row}"


def get_target_sheets(wb: xw.Book, pattern: str) -> List[xw.Sheet]:
    """対象シートをシート名の正規表現で抽出する"""
    target_sheets = []
    regex = re.compile(pattern)
    for sheet in wb.sheets:
        if regex.match(sheet.name):
            target_sheets.append(sheet)
    return target_sheets


class ExcelEditor:
    """Excelのシートに対する操作をまとめたクラス"""

    def __init__(self, sheet: xw.Sheet, debug: bool = False):
        self.sheet = sheet
        self.debug = debug

    def _debug_log(self, message: str):
        if self.debug:
            print(f"[DEBUG] {self.sheet.name}: {message}")

    def find_row_by_keyword(
        self, col: str, keyword: str, start_row: int = 1, end_row: int = 1000
    ) -> Optional[int]:
        """指定列をキーワード検索してヒットした最初の行番号を取得

        Args:
            col (str): 検索対象の列レター（例: "A"）
            keyword (str): 検索するキーワード
            start_row (int): 検索開始行（デフォルト: 1）
            end_row (int): 検索終了行（デフォルト: 1000）

        Returns:
            Optional[int]: 見つかった場合の行番号、見つからなかった場合はNone
        """
        values = self.sheet.range(f"{col}{start_row}:{col}{end_row}").value
        if not values:
            return None
        # 単一セルの場合はリスト化
        if type(values) is not list:
            values = [values]

        for i, val in enumerate(values):
            # print(f"[DEBUG] {self.sheet.name}: {col}{start_row + i} : {val}")
            if val == keyword:
                return start_row + i
        return None

    def find_col_by_keyword(
        self, row: int, keyword: str, start_col: str = "A", end_col: str = "DZ"
    ) -> Optional[str]:
        """指定行をキーワード検索してヒットした最初の列レターを取得

        Args:
            row (int): 検索対象の行番号
            keyword (str): 検索するキーワード
            start_col (str): 検索開始列レター（デフォルト: "A"）
            end_col (str): 検索終了列レター（デフォルト: "DZ"）

        Returns:
            Optional[str]: 見つかった場合の列レター、見つからなかった場合はNone
        """
        values = self.sheet.range(f"{start_col}{row}:{end_col}{row}").value
        if not values:
            return None
        # 単一セルの場合はリスト化
        if type(values) is not list:
            values = [values]

        start_col_num = col_letter_to_num(start_col)
        for i, val in enumerate(values):
            if val == keyword:
                return col_num_to_letter(start_col_num + i)
        return None

    def get_range(self, address: str) -> xw.Range:
        """対象の範囲を取得する

        Args:
            address (str): シート内の範囲（例: "A2", "A2:D3"）

        Returns:
            xw.Range: xlwingsのRangeオブジェクト
        """
        return self.sheet.range(address)

    def set_value(self, address: str, value: Any):
        """指定した範囲の値設定

        Args:
            address (str): 対象のセルまたは範囲（例: "A1", "A1:B2"）
            value (Any): 設定する値
        """
        self._debug_log(f"値設定: 範囲={address}, 値={value}")
        self.sheet.range(address).value = value

    def set_font_size(self, address: str, size: int):
        """指定した範囲のフォントサイズ設定

        Args:
            address (str): 対象のセルまたは範囲
            size (int): フォントサイズ（ポイント数）
        """
        self._debug_log(f"フォントサイズ変更: 範囲={address}, サイズ={size}")
        self.sheet.range(address).font.size = size

    def set_font_name(self, address: str, name: str):
        """指定した範囲のフォント設定

        Args:
            address (str): 対象のセルまたは範囲
            name (str): フォント名（例: "Meiryo UI"）
        """
        self._debug_log(f"フォント名変更: 範囲={address}, フォント={name}")
        self.sheet.range(address).font.name = name

    def set_background_color(self, address: str, color: Tuple[int, int, int]):
        """指定した範囲の背景色設定

        Args:
            address (str): 対象のセルまたは範囲
            color (Tuple[int, int, int]): RGBタプル (例: (255, 0, 0))
        """
        self._debug_log(f"背景色設定: 範囲={address}, RGB={color}")
        self.sheet.range(address).color = color

    def set_borders(
        self,
        address: str,
        line_style: int = xlContinuous,
        weight: int = xlThin,
        position: Optional[list] = None,
    ):
        """指定した範囲の罫線設定

        Args:
            address (str): 対象のセルまたは範囲
            line_style (int): 罫線の種類（デフォルト: xlContinuous(1)等）
            weight (int): 罫線の太さ（デフォルト: xlThin(2)等）
            position (Optional[list]): 罫線を引く位置のリスト(例: [xlEdgeBottom, xlEdgeTop])。未指定時は全てに引く。
        """
        self._debug_log(
            f"罫線設定: 範囲={address}, 種類={line_style}, 太さ={weight}, 位置={position}"
        )
        rng = self.sheet.range(address)
        if position is None:
            borders = (
                xlEdgeLeft,
                xlEdgeTop,
                xlEdgeBottom,
                xlEdgeRight,
                xlInsideVertical,
                xlInsideHorizontal,
            )
        else:
            if not isinstance(position, list):
                borders = (position,)
            else:
                borders = tuple(position)

        for border_id in borders:
            try:
                rng.api.Borders(border_id).LineStyle = line_style
                if line_style != xlLineStyleNone:
                    rng.api.Borders(border_id).Weight = weight
            except Exception as e:
                # 範囲が1セルの場合など、Inside系の設定はエラーになるため無視する
                self._debug_log(
                    f"罫線の設定でエラーが発生しました (border_id={border_id}): {e}"
                )
                pass

    def set_alignment(
        self,
        address: str,
        horizontal: Optional[int] = None,
        vertical: Optional[int] = None,
    ):
        """指定した範囲のアライン（センタリングなど）設定

        Args:
            address (str): 対象のセルまたは範囲
            horizontal (Optional[int]): 水平方向のアラインメント定数（例: xlHAlignCenter）
            vertical (Optional[int]): 垂直方向のアラインメント定数（例: xlVAlignCenter）
        """
        self._debug_log(
            f"アライン変更: 範囲={address}, 水平={horizontal}, 垂直={vertical}"
        )
        rng = self.sheet.range(address)
        if horizontal is not None:
            rng.api.HorizontalAlignment = horizontal
        if vertical is not None:
            rng.api.VerticalAlignment = vertical

    def set_text_control(
        self,
        address: str,
        wrap_text: Optional[bool] = None,
        shrink_to_fit: Optional[bool] = None,
    ):
        """指定した範囲の文字の「折り返して全体を表示」／「縮小して全体を表示」設定

        Args:
            address (str): 対象のセルまたは範囲
            wrap_text (Optional[bool]): Trueの場合「折り返して全体を表示」
            shrink_to_fit (Optional[bool]): Trueの場合「縮小して全体を表示」
        """
        self._debug_log(
            f"テキスト制御: 範囲={address}, 折り返し={wrap_text}, 縮小={shrink_to_fit}"
        )
        rng = self.sheet.range(address)
        if wrap_text is not None:
            rng.api.WrapText = wrap_text
        if shrink_to_fit is not None:
            rng.api.ShrinkToFit = shrink_to_fit

    def set_merge(self, address: str, merge: bool = True):
        """指定した範囲のセルを結合／結合解除

        Args:
            address (str): 対象の範囲
            merge (bool): Trueで結合、Falseで結合解除（デフォルト: True）
        """
        self._debug_log(f"セル結合/解除: 範囲={address}, 結合={merge}")
        if merge:
            self.sheet.range(address).api.Merge()
        else:
            self.sheet.range(address).api.UnMerge()

    def set_number_format(self, address: str, format_str: str):
        """指定した範囲の表示形式設定

        Args:
            address (str): 対象のセルまたは範囲
            format_str (str): 表示形式（例: '@' で文字列、'#,##0' でカンマ区切り数値など）
        """
        self._debug_log(f"表示形式設定: 範囲={address}, 書式={format_str}")
        self.sheet.range(address).number_format = format_str

    def delete_rows(self, start_row: int, end_row: int):
        """指定した行範囲の削除

        Args:
            start_row (int): 削除開始行
            end_row (int): 削除終了行
        """
        self._debug_log(f"行削除: 行数={start_row}～{end_row}")
        self.sheet.range(f"{start_row}:{end_row}").api.Delete()

    def delete_cols(self, start_col: str, end_col: str):
        """指定した列範囲の削除

        Args:
            start_col (str): 削除開始列レター
            end_col (str): 削除終了列レター
        """
        self._debug_log(f"列削除: 列={start_col}～{end_col}")
        self.sheet.range(f"{start_col}:{end_col}").api.Delete()

    def delete_range(
        self, address: Any, shift_up: bool = True, shift_left: bool = False
    ):
        """指定した範囲を削除して左／上方向にシフト

        Args:
            address (Union[str, xw.Range]): 対象の範囲アドレス（例: "A1:B2"）または Rangeオブジェクト
            shift_up (bool): Trueの場合、上方向にシフト（デフォルト: True。shift_leftが指定された場合はそちらを優先）
            shift_left (bool): Trueの場合、左方向にシフト
        """
        shift_val = xlToLeft if shift_left else (xlUp if shift_up else xlToLeft)
        if isinstance(address, str):
            self._debug_log(
                f"範囲削除: 範囲={address}, 上シフト={shift_up}, 左シフト={shift_left}"
            )
            self.sheet.range(address).api.Delete(Shift=shift_val)
        else:
            self._debug_log(
                f"範囲削除: 範囲={address.address}, 上シフト={shift_up}, 左シフト={shift_left}"
            )
            address.api.Delete(Shift=shift_val)

    def insert_range(
        self, address: Any, shift_down: bool = True, shift_right: bool = False
    ):
        """指定した範囲を挿入して右／下方向にシフト

        Args:
            address (Union[str, xw.Range]): 対象の範囲アドレス（例: "A1:B2"）または Rangeオブジェクト
            shift_down (bool): Trueの場合、下方向にシフト（デフォルト: True。shift_rightが指定された場合はそちらを優先）
            shift_right (bool): Trueの場合、右方向にシフト
        """
        shift_val = xlToRight if shift_right else (xlDown if shift_down else xlToRight)
        if isinstance(address, str):
            self._debug_log(
                f"範囲挿入: 範囲={address}, 下シフト={shift_down}, 右シフト={shift_right}"
            )
            self.sheet.range(address).api.Insert(Shift=shift_val)
        else:
            self._debug_log(
                f"範囲挿入: 範囲={address.address}, 下シフト={shift_down}, 右シフト={shift_right}"
            )
            address.api.Insert(Shift=shift_val)

    def set_page_setup(
        self,
        orientation: Optional[int] = None,
        fit_width: Optional[int] = None,
        fit_height: Optional[int] = None,
    ):
        """ページ設定・次のページ数に合わせて印刷

        Args:
            orientation (Optional[int]): 印刷の向き（例: xlLandscape, xlPortrait）
            fit_width (Optional[int]): 横に合わせて印刷するページ数（未指定の場合は制約なし）
            fit_height (Optional[int]): 縦に合わせて印刷するページ数（未指定の場合は制約なし）
        """
        self._debug_log(
            f"ページ設定: 向き={orientation}, 横幅={fit_width}, 縦幅={fit_height}"
        )
        if orientation is not None:
            self.sheet.api.PageSetup.Orientation = orientation

        if fit_width is not None or fit_height is not None:
            self.sheet.api.PageSetup.Zoom = False
            # False を設定することでその方向への制約をなくす
            self.sheet.api.PageSetup.FitToPagesWide = (
                fit_width if fit_width is not None else False
            )
            self.sheet.api.PageSetup.FitToPagesTall = (
                fit_height if fit_height is not None else False
            )

    def set_print_area(self, address: str):
        """印刷範囲の設定

        Args:
            address (str): 印刷範囲とするアドレス（例: "A1:G50"）
        """
        self._debug_log(f"印刷範囲設定: 範囲={address}")
        self.sheet.api.PageSetup.PrintArea = address

    def insert_copied_rows(self, src_sheet: xw.Sheet, src_row_str: str, dest_row: int):
        """テンプレートファイル等からコピーした行を、指定行に挿入

        Args:
            src_sheet (xw.Sheet): コピー元のシート
            src_row_str (str): コピー元の行範囲（例: "1:3"）
            dest_row (int): 挿入先の行番号
        """
        self._debug_log(
            f"行コピー挿入: 元範囲='{src_sheet.name}'!{src_row_str}, 挿入先={dest_row}行目"
        )
        src_sheet.range(src_row_str).api.Copy()
        self.sheet.range(f"{dest_row}:{dest_row}").api.Insert(Shift=xlDown)

    def insert_copied_cols(self, src_sheet: xw.Sheet, src_col_str: str, dest_col: str):
        """テンプレートファイル等からコピーした列を、指定列に挿入

        Args:
            src_sheet (xw.Sheet): コピー元のシート
            src_col_str (str): コピー元の列範囲（例: "A:D"）
            dest_col (str): 挿入先の列レター
        """
        self._debug_log(
            f"列コピー挿入: 元範囲='{src_sheet.name}'!{src_col_str}, 挿入先={dest_col}列目"
        )
        src_sheet.range(src_col_str).api.Copy()
        self.sheet.range(f"{dest_col}:{dest_col}").api.Insert(Shift=xlToRight)

    def paste_shape(self, src_sheet: xw.Sheet, shape_name: str, dest_cell: str):
        """テンプレートファイルからコピーしたシェイプを、指定位置(セル)に貼り付け

        Args:
            src_sheet (xw.Sheet): コピー元のシート
            shape_name (str): コピー元のシェイプ名
            dest_cell (str): 貼り付け先のセル
        """
        self._debug_log(
            f"シェイプ貼り付け: 元シェイプ='{src_sheet.name}'!{shape_name}, 貼付先={dest_cell}"
        )
        src_shape = src_sheet.shapes[shape_name]
        src_shape.api.Copy()
        self.sheet.range(dest_cell).api.Select()
        self.sheet.api.Paste()

    def delete_shapes_by_text(self, text: str):
        """指定した文字列でシェイプを検索し、ヒットしたシェイプを削除

        Args:
            text (str): 削除対象のシェイプに含まれる文字列、またはシェイプ名
        """
        self._debug_log(f"シェイプ削除: 検索文字列='{text}'")
        shapes_to_delete = []

        for shape in self.sheet.shapes:
            try:
                # TextFrame2からのテキスト取得を試行
                shape_text = shape.api.TextFrame2.TextRange.Text
                if text in shape_text:
                    shapes_to_delete.append(shape)
                    continue
            except Exception:
                pass

            try:
                # 代替のTextFrameからのテキスト取得を試行
                shape_text = shape.api.TextFrame.Characters().Text
                if text in shape_text:
                    shapes_to_delete.append(shape)
                    continue
            except Exception:
                pass

            # 図形の名前自体に含まれる場合
            if text in shape.name:
                shapes_to_delete.append(shape)

        for shape in shapes_to_delete:
            try:
                shape.delete()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description="Excelフォーマット一括修正ツール")
    parser.add_argument(
        "--target-dir",
        "-t",
        type=str,
        default=TARGET_DIR,
        help=f"対象ファイルがあるフォルダ (デフォルト: {TARGET_DIR})",
    )
    parser.add_argument(
        "--backup-dir",
        "-b",
        type=str,
        default=BACKUP_DIR,
        help=f"バックアップフォルダ (デフォルト: {BACKUP_DIR})",
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="デバッグオプション。指定された場合、編集操作内容を標準出力に出力します。",
    )
    args = parser.parse_args()

    # Windowsでターミナルの出力が文字化けしないための対応
    # if os.name == "nt":
    #     os.system("chcp 65001")

    # Excelアプリケーションを起動（visible=Trueにすると動いている様子が見えます）
    # 完全に裏で動かしたい場合は visible=False に変更してください。
    app = xw.App(visible=False, add_book=False)

    try:
        # コピー元のテンプレートファイルを開く
        wb_template = app.books.open(TEMPLATE_FILE)
        sh_template = wb_template.sheets[TEMPLATE_SHEET]

        # 指定ディレクトリ内の .xlsx ファイルを全て取得
        target_dir_path = pathlib.Path(args.target_dir)
        excel_files = target_dir_path.glob("*.xlsx")

        # バックアップディレクトリの準備
        backup_dir_path = pathlib.Path(args.backup_dir)
        backup_dir_path.mkdir(parents=True, exist_ok=True)

        for file_path in excel_files:
            # テンプレートファイル自身が同じフォルダにある場合はスキップ
            if file_path.name == pathlib.Path(TEMPLATE_FILE).name:
                continue

            print("=" * 60)

            # --- バックアップ処理 ---
            backup_file_path = backup_dir_path / file_path.name
            if not backup_file_path.exists():
                shutil.copy2(file_path, backup_file_path)
            else:
                print(f"バックアップスキップ (既に存在します): {backup_file_path.name}")

            print(f"処理開始: {file_path.name}")
            wb = app.books.open(file_path)

            try:
                # ==========================================
                # 以下の処理は要件に合わせて自由にカスタマイズしてください
                # ==========================================
                # 以下はサンプル実装：デジタル庁のAPI仕様書フォーマットを変換
                # https://www.digital.go.jp/policies/local_governments/common-feature-specification#latest-documents

                # 正規表現による対象シートの取得
                sheet_pattern = (
                    r"レスポンス_API仕様.*"  # 対象シート名の規則（正規表現）
                )
                target_sheets = get_target_sheets(wb, sheet_pattern)

                for sheet in target_sheets:
                    print("-" * 60)
                    print(f"  シート処理中: {sheet.name}")
                    editor = ExcelEditor(sheet, debug=args.debug)

                    # A5セルの値を変更
                    editor.set_value("A5", "ID")

                    # A列の値が「■正常系（HTTPステータスコード：200、JSON形式でのレスポンス）」の行を検索
                    target_section_start_row = editor.find_row_by_keyword(
                        "A",
                        "■正常系（HTTPステータスコード：200、JSON形式でのレスポンス）　",
                    )
                    if target_section_start_row:
                        # target_section_start_rowの2行後から4行後までを削除
                        editor.delete_rows(
                            target_section_start_row + 2,
                            target_section_start_row + 4,
                        )

                        # target_section_start_rowの2行後からテンプレートの11行目から13行目をコピーして挿入
                        editor.insert_copied_rows(
                            sh_template, "11:13", target_section_start_row + 2
                        )

                    # A列の値が「項番」の行を検索
                    target_section_start_row = editor.find_row_by_keyword(
                        "A",
                        "項番",
                    )
                    # A列の値が「エラーコード一覧」の行を検索
                    next_section_start_row = editor.find_row_by_keyword(
                        "A",
                        "エラーコード一覧",
                    )
                    if target_section_start_row and next_section_start_row:
                        target_section_end_row = next_section_start_row - 1
                        header_row = target_section_start_row

                        # ヘッダ「必須」「null設定有無」の列数を修正
                        #   1-1. 「必須」ヘッダ(2行3列)のセル結合を解除
                        target_col = editor.find_col_by_keyword(header_row, "必須")
                        editor.set_merge(
                            get_range_address(f"{target_col}{header_row}", 2, 3),
                            merge=False,
                        )
                        #   1-2. 「必須」ヘッダ開始列の1列右の列を削除
                        delete_col = get_col_by_offset(target_col, 1)
                        target_range = editor.get_range(
                            f"{delete_col}{header_row}:{delete_col}{target_section_end_row}"
                        )
                        editor.delete_range(target_range, shift_left=True)
                        #   1-3. 「必須」ヘッダ(2行2列)のセル結合
                        editor.set_merge(
                            get_range_address(f"{target_col}{header_row}", 2, 2),
                            merge=True,
                        )

                        #   2-1. 「null設定有無」ヘッダ(2行4列)のセル結合を解除
                        target_col = editor.find_col_by_keyword(
                            header_row, "null設定有無"
                        )
                        editor.set_merge(
                            get_range_address(f"{target_col}{header_row}", 2, 4),
                            merge=False,
                        )
                        #   2-2. 「null設定有無」ヘッダ開始列の1列右に1列追加
                        insert_col = get_col_by_offset(target_col, 1)
                        target_range = editor.get_range(
                            f"{insert_col}{header_row}:{insert_col}{target_section_end_row}"
                        )
                        editor.insert_range(target_range, shift_right=True)
                        #   2-3. 「null設定有無」ヘッダ(2行5列)のセル結合
                        editor.set_merge(
                            get_range_address(f"{target_col}{header_row}", 2, 5),
                            merge=True,
                        )

                        # 「レスポンスオブジェクト名」の列（I～AE）の垂直な内側罫線を無しにする
                        data_start_row = target_section_start_row + 3
                        data_end_row = target_section_end_row
                        data_range = editor.get_range(
                            f"I{data_start_row}:AE{data_end_row}"
                        )
                        editor.set_borders(
                            f"I{data_start_row}:AE{data_end_row}",
                            line_style=xlLineStyleNone,
                            position=xlInsideVertical,
                        )

                    # ページ・印刷設定
                    editor.set_page_setup(
                        orientation=xlPortrait, fit_height=2, fit_width=1
                    )  # 縦向き、縦2ページ

            except Exception as e:
                print(f"エラーが発生しました: {e}")
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
