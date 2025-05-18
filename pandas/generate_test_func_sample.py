import json

# テスト仕様データ（例として直接記載。実際はファイルから読み込んでもOK）
test_spec = {
    "項目1.1.1": [
        {
            "大分類": 1,
            "中分類": 1,
            "小分類": 1,
            "種別": "概要",
            "種別補助No.": "-",
            "内容": "テストの概要（文章のみ）",
        },
        {
            "大分類": 1,
            "中分類": 1,
            "小分類": 1,
            "種別": "観点",
            "種別補助No.": "-",
            "内容": "テストの観点（文章のみ）",
        },
        {
            "大分類": 1,
            "中分類": 1,
            "小分類": 1,
            "種別": "前提条件",
            "種別補助No.": "-",
            "内容": "テストの前提条件（文章のみ）",
        },
        {
            "大分類": 1,
            "中分類": 1,
            "小分類": 1,
            "種別": "事前準備_SQL",
            "種別補助No.": 1,
            "内容": "手順の前に実行するSQL",
        },
        {
            "大分類": 1,
            "中分類": 1,
            "小分類": 1,
            "種別": "手順_HTTPリクエスト",
            "種別補助No.": 1,
            "内容": 'URL=XXX\nMETHOD=XXX\nPOST_DATA="xxx"',
        },
        {
            "大分類": 1,
            "中分類": 1,
            "小分類": 1,
            "種別": "判定方法_HTTPレスポンス",
            "種別補助No.": 1,
            "内容": "HTTPレスポンスと比較するJSON",
        },
        {
            "大分類": 1,
            "中分類": 1,
            "小分類": 1,
            "種別": "判定方法_SQL",
            "種別補助No.": 1,
            "内容": "結果判定のために実行するSQL",
        },
        {
            "大分類": 1,
            "中分類": 1,
            "小分類": 1,
            "種別": "判定方法_SQL",
            "種別補助No.": 2,
            "内容": "結果判定のために実行するSQL",
        },
    ],
    "項目1.1.2": [
        {
            "大分類": 1,
            "中分類": 1,
            "小分類": 2,
            "種別": None,
            "種別補助No.": None,
            "内容": None,
        }
    ],
    "項目1.2.1": [
        {
            "大分類": 1,
            "中分類": 2,
            "小分類": 1,
            "種別": None,
            "種別補助No.": None,
            "内容": None,
        }
    ],
}


def parse_http_request(content):
    """HTTPリクエスト仕様からURL/METHOD/POST_DATAを抽出"""
    lines = content.split("\n")
    url, method, post_data = "", "", ""
    for line in lines:
        if line.startswith("URL="):
            url = line[4:]
        elif line.startswith("METHOD="):
            method = line[7:]
        elif line.startswith("POST_DATA="):
            post_data = line[10:]
    return url, method, post_data


def generate_pytest_code(spec):
    code_lines = ["import pytest", "import requests", "", "# pytest自動生成コード", ""]
    for item_key, steps in spec.items():
        # テスト関数名
        func_name = f"test_{item_key.replace('.', '_')}"
        # コメント用
        overview = ""
        viewpoint = ""
        precondition = ""
        setup_sql = []
        http_req = None
        http_resp = None
        judge_sql = []
        for step in steps:
            if not step.get("種別"):
                continue
            if step["種別"] == "概要":
                overview = step["内容"]
            elif step["種別"] == "観点":
                viewpoint = step["内容"]
            elif step["種別"] == "前提条件":
                precondition = step["内容"]
            elif step["種別"] == "事前準備_SQL":
                setup_sql.append(step["内容"])
            elif step["種別"] == "手順_HTTPリクエスト":
                http_req = step["内容"]
            elif step["種別"] == "判定方法_HTTPレスポンス":
                http_resp = step["内容"]
            elif step["種別"] == "判定方法_SQL":
                judge_sql.append(step["内容"])
        code_lines.append(f"def {func_name}():")
        if overview:
            code_lines.append(f"    '''{overview}'''")
        if viewpoint:
            code_lines.append(f"    # 観点: {viewpoint}")
        if precondition:
            code_lines.append(f"    # 前提条件: {precondition}")
        if setup_sql:
            code_lines.append("    # 事前準備SQL")
            for sql in setup_sql:
                code_lines.append(f"    # 実行SQL: {sql}")
                code_lines.append("    # db.execute(sql)  # ←実装例")
        if http_req:
            url, method, post_data = parse_http_request(http_req)
            code_lines.append("    # HTTPリクエスト送信")
            code_lines.append(f"    url = '{url}'")
            code_lines.append(f"    method = '{method}'")
            code_lines.append(f"    data = {post_data}")
            code_lines.append(
                "    # response = requests.request(method, url, json=data)"
            )
            code_lines.append("    # assert response.status_code == 200")
        if http_resp:
            code_lines.append("    # HTTPレスポンス判定")
            code_lines.append(f"    expected_response = {http_resp}")
            code_lines.append("    # assert response.json() == expected_response")
        if judge_sql:
            code_lines.append("    # 判定用SQL")
            for sql in judge_sql:
                code_lines.append(f"    # 判定SQL: {sql}")
                code_lines.append("    # result = db.execute(sql)")
                code_lines.append("    # assert ...  # 判定ロジックを記述")
        code_lines.append("")
    return "\n".join(code_lines)


if __name__ == "__main__":
    code = generate_pytest_code(test_spec)
    with open("generated_test.py", "w", encoding="utf-8") as f:
        f.write(code)
    print("generated_test.py を出力しました。")
