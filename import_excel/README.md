# Excel Import & CLI Execution Template

Excelファイルから特定の列（「No.」「値１」「値２」）を読み込み、テキストファイルを生成した上で、そのファイルに対してCLIコマンドを実行するための汎用的なPythonテンプレートです。

## 特徴
- 各行のデータに対する処理が明確に2つの関数に分かれており、カスタマイズが容易です。
  1. `process_row_data`: Excelから読み込んだ値を用いてディレクトリやファイルを作成する処理
  2. `execute_cli_command`: 作成したファイルに対してCLIコマンドを実行する処理
- `argparse` により柔軟に実行オプションを指定できます。
- 型ヒント（`TypedDict` 等）と `logging` モジュールによるロギングを標準搭載しています。

## 前提条件
- Python 3.9 以上を推奨
- 必要なパッケージのインストール

```bash
# 本番実行向け
pip install -r requirements.txt

# 開発・テスト向け
pip install -r requirements-dev.txt
```

## 使用方法

### 1. Excelファイルの準備
以下のようなヘッダー（1行目）をもつExcelファイルを用意してください。

| No. | 値１   | 値２             |
|-----|--------|------------------|
| 1   | sample | 任意のテキスト   |
| 2   | test   | コマンド引数など |

### 2. 独自の処理へのカスタマイズ
`main.py` 内の以下の関数を、要件に合わせて書き換えてください。

- `process_row_data(row_data, output_dir)`
  - 例えばディレクトリ階層を深くする、ファイルフォーマットをJSONに変更する、など。
- `execute_cli_command(target_file, row_data)`
  - 初期状態ではダミーとして `echo` コマンドを実行するようになっています。
  - 実際に実行したいCLIツールや引数に合わせて `cmd` リストを書き換えてください。

### 3. 実行

```bash
python main.py data.xlsx --sheet "Sheet1" --outdir "output_folder"
```

#### 引数
- `input_file` (必須): 入力用のExcelファイルのパス
- `--sheet`: 読み込むシート名またはインデックス（デフォルト: 最初のシート）
- `--outdir`: 出力先ディレクトリ（デフォルト: `./output`）

## フォーマットと静的解析 (開発時)
当プロジェクトは PEP8 に準拠し、Black フォーマッターと mypy による型検査を想定しています。

```bash
# フォーマット
black main.py

# Lint / 型チェック
flake8 main.py
mypy main.py
```
