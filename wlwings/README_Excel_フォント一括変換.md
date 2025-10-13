
# Excel一括フォント変換ツール（Python + xlwings）

指定Excelファイル、もしくは、指定フォルダ配下のExcelファイルを、一括でPDFに変換します。  

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
```

## 実行方法
### バッチファイル
```bat
run_convert_font.bat "C:\path\to\input"
```

### シェルスクリプト (Git for windows)
```
./run_convert_font.sh "/path/to/input"
```
