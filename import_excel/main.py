import argparse
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import TypedDict

import pandas as pd

# ログの設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ExcelRowData(TypedDict):
    """
    Excelから読み込んだ1行分のデータを表す型定義
    """

    no: str
    value1: str
    value2: str


def sanitize_filename(filename: str) -> str:
    """
    ファイル名として使用できない文字をアンダースコアに置換するサニタイズ処理
    """
    return re.sub(r'[\\/:*?"<>|]+', "_", str(filename))


def process_row_data(row_data: ExcelRowData, output_dir: Path) -> Path | None:
    """
    1. 読み込んだ値を使って実行する処理（ディレクトリ・ファイル作成など）

    Args:
        row_data (ExcelRowData): Excelから読み込んだ1行分のデータ
        output_dir (Path): 出力先ディレクトリ

    Returns:
        Path | None: 生成したファイルのパス。生成しなかった場合やエラー時はNone。
    """
    try:
        no = row_data["no"]
        val1 = row_data["value1"]
        val2 = row_data["value2"]

        # 必須項目が空の場合はスキップするなどの制御を入れることも可能
        if not no or not val1:
            logger.warning(f"No. または 値１ が空のためスキップします: {row_data}")
            return None

        # ファイル名の生成: <No.>/<値１>.txt
        safe_val1 = sanitize_filename(val1)
        file_name = f"{safe_val1}.txt"

        # No.ごとのディレクトリを作成
        dir_path = output_dir / str(no)
        dir_path.mkdir(parents=True, exist_ok=True)

        file_path = dir_path / file_name

        # 「値２」をファイルに書き込む
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(str(val2))

        logger.info(f"ファイルを作成しました: {file_path}")
        return file_path

    except Exception as e:
        logger.error(f"ファイル作成処理でエラーが発生しました (row: {row_data}): {e}")
        return None


def execute_cli_command(target_file: Path, row_data: ExcelRowData) -> None:
    """
    2. 1で作成したものに対して実行する処理（CLIコマンドなど）

    Args:
        target_file (Path): 1の処理で生成された対象ファイル
        row_data (ExcelRowData): Excelから読み込んだ1行分のデータ
    """
    try:
        # 実行するコマンドの構築
        # 以下はダミーとして、echoコマンドで対象ファイル名を出力する例
        cmd = ["echo", f"実行対象ファイル: {target_file}"]

        # Windowsにおいてecho等を実行する場合は shell=True が必要なケースがあるが、
        # 本格的なCLIコマンドを実行する場合は適宜変更すること。
        # 例: cmd = ["my_cli_tool", "--input", str(target_file), "--param", row_data["value1"]]

        # subprocess経由でコマンド実行
        # stdoutの内容を取得したい場合は capture_output=True, text=True を付与する
        result = subprocess.run(
            cmd, check=True, capture_output=True, text=True, shell=True
        )

        logger.info(f"コマンドの実行に成功しました: {' '.join(cmd)}")
        if result.stdout:
            logger.debug(f"コマンド標準出力: {result.stdout.strip()}")

    except subprocess.CalledProcessError as e:
        logger.error(f"CLIコマンドの実行に失敗しました (file: {target_file}): {e}")
        if e.stderr:
            logger.error(f"エラー詳細: {e.stderr.strip()}")
    except Exception as e:
        logger.error(f"予期せぬエラーが発生しました (file: {target_file}): {e}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Excelファイルを読み込み、ファイル生成とCLIコマンド実行を行うテンプレートスクリプト"
    )
    parser.add_argument("input_file", type=str, help="入力用のExcelファイルのパス")
    parser.add_argument(
        "--sheet",
        type=str,
        default=0,
        help="読み込むシート名またはインデックス（デフォルト: 最初のシート）",
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default="output",
        help="出力先ディレクトリ（デフォルト: ./output）",
    )

    args = parser.parse_args()

    input_path = Path(args.input_file)
    output_dir = Path(args.outdir)

    # 入力ファイルの存在確認
    if not input_path.exists():
        logger.error(f"入力ファイルが見つかりません: {input_path}")
        sys.exit(1)

    # 出力先ディレクトリが存在しない場合は作成
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Excelファイルの読み込み
        logger.info(f"Excelファイルを読み込みます: {input_path}")
        # header=0がデフォルト。欠損値は空文字に置換することで扱いやすくする。
        df = pd.read_excel(input_path, sheet_name=args.sheet)
        df = df.fillna("")

        # 必須カラムのチェック
        required_columns = ["No.", "値１", "値２"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"入力ファイルに必要な列が不足しています: {missing_columns}")
            sys.exit(1)

        logger.info(f"全 {len(df)} 件のデータを処理します。")

        # 各行に対して処理を実行
        for index, row in df.iterrows():
            # 行データを TypedDict にマッピング
            # pandas等の型推論により float になる場合があるため str に変換
            # 'No.' が '1.0' のようになるのを防ぐ場合は int() などを経由することも検討

            # 簡易的に文字列にする
            no_val = str(row["No."]).strip()
            # もし '1.0' のような数値表記が含まれるなら以下のように整形可能
            if no_val.endswith(".0"):
                no_val = no_val[:-2]

            row_data: ExcelRowData = {
                "no": no_val,
                "value1": str(row["値１"]).strip(),
                "value2": str(row["値２"]).strip(),
            }

            # 1. 読み込んだ値を使って実行する処理
            created_file = process_row_data(row_data, output_dir)

            # ファイルが正常に作成された場合のみ次の処理へ
            if created_file and created_file.exists():
                # 2. 1で作成したものに対して実行する処理
                execute_cli_command(created_file, row_data)

        logger.info("すべての処理が完了しました。")

    except ValueError as e:
        logger.error(f"Excelの読み込みエラー（シートが見つからない等）: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"予期せぬエラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
