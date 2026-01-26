# WSDL Parser

SOAPのWSDLファイルを解析して、読みやすい形式で出力するPythonツールです。

## 概要

WSDLファイルまたはURLからWSDL定義を取得し、以下の情報を整形して出力します：

- **サービス情報**: サービス名、ポート、エンドポイントURL
- **オペレーション一覧**: メソッド名、入出力メッセージ、SOAPAction
- **メッセージ定義**: パラメータ名と要素/型の参照
- **データ型定義**: ComplexType、Element、フィールド情報、xsd:annotation/xsd:documentationからの説明文

## 特徴

- ローカルファイルとURLの両方に対応
- テキスト形式・HTML形式での出力をサポート
- HTML出力では要素間のリンクナビゲーションが可能
- 接続エラー時の自動リトライ機能

## 必要環境

- Python 3.10以上
- 依存ライブラリ
  - lxml
  - requests

## インストール

```bash
# 仮想環境の作成（任意）
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 依存ライブラリのインストール
pip install -r requirements.txt
```

## 使い方

### 基本的な使用方法

```bash
# ローカルファイルを解析（テキスト出力）
python wsdl_parser.py <WSDLファイルのパス>

# URLから取得して解析
python wsdl_parser.py <WSDL URL>
```

### オプション

| オプション | 短縮形 | 説明 |
|-----------|-------|------|
| `--output <ファイル名>` | `-o` | 出力ファイルを指定（未指定時は標準出力） |
| `--format <形式>` | `-f` | 出力形式を指定（`text` または `html`、デフォルト: `text`） |

### 使用例

```bash
# テキスト形式で標準出力
python wsdl_parser.py service.wsdl

# URLから取得してHTML形式でファイル出力
python wsdl_parser.py http://example.com/service?wsdl --format html --output result.html

# ローカルファイルをHTML形式で出力
python wsdl_parser.py service.wsdl -f html -o result.html
```

## 出力例

### テキスト形式

```
================================================================================
WSDL解析結果
================================================================================

ターゲット名前空間: http://example.com/services

================================================================================
📡 サービス情報
================================================================================

【サービス名】 ExampleService
  ├─ ポート: ExamplePort
  │  ├─ バインディング: ExampleBinding
  │  └─ エンドポイント: http://example.com/service
```

### HTML形式

HTML形式では以下の機能を提供します：

- 📑 目次からセクションへのジャンプ
- 🔗 メッセージ・データ型間のリンクナビゲーション
- 🎨 視覚的に分かりやすいテーブル表示
- ✨ ターゲット要素のハイライトアニメーション

## 対応するWSDL要素

- `wsdl:service` - サービス定義
- `wsdl:port` - ポート定義
- `wsdl:binding` - バインディング定義
- `wsdl:portType` - ポートタイプ（インターフェース）定義
- `wsdl:operation` - オペレーション定義
- `wsdl:message` - メッセージ定義
- `xsd:complexType` - 複合型定義
- `xsd:element` - 要素定義

## 開発

### 開発環境のセットアップ

```bash
# 開発用依存ライブラリのインストール
pip install -r requirements-dev.txt
```

### コードフォーマット

```bash
# Blackによる自動フォーマット
black wsdl_parser.py

# isortによるインポート整理
isort wsdl_parser.py
```

### 型チェック

```bash
mypy wsdl_parser.py
```

### 実行ファイル化

```bash
pyinstaller --onefile wsdl_parser.py
```

