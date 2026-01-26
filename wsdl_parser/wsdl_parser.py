#!/usr/bin/env python3
"""
WSDL Parser - SOAPのWSDLファイルを解析して読みやすく出力するツール

使い方:
  python wsdl_parser.py <wsdlファイルのパス>
  python wsdl_parser.py <URL>
  python wsdl_parser.py <wsdlファイルのパス> --output result.html
  python wsdl_parser.py <wsdlファイルのパス> --format text

必要なライブラリ:
  pip install lxml requests
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
from lxml import etree


class WSDLParser:
    """WSDLファイルを解析するクラス"""

    NAMESPACES = {
        "wsdl": "http://schemas.xmlsoap.org/wsdl/",
        "soap": "http://schemas.xmlsoap.org/wsdl/soap/",
        "soap12": "http://schemas.xmlsoap.org/wsdl/soap12/",
        "xsd": "http://www.w3.org/2001/XMLSchema",
        "http": "http://schemas.xmlsoap.org/wsdl/http/",
    }

    def __init__(self, wsdl_source: str):
        """
        Args:
            wsdl_source: WSDLファイルのパスまたはURL
        """
        self.wsdl_source = wsdl_source
        self.tree: etree._Element | etree._ElementTree | None = None
        self.root: etree._Element | None = None
        self.target_namespace: str | None = None

    def load_wsdl(self) -> bool:
        """WSDLファイルをロードする"""
        try:
            # URLかローカルファイルかを判定
            parsed_url = urlparse(self.wsdl_source)
            if parsed_url.scheme in ["http", "https"]:
                print(f"URLからWSDLを取得中: {self.wsdl_source}")
                # ブラウザを模倣したヘッダーを設定
                headers = {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Accept": "text/xml, application/xml, */*",
                }
                # リトライ機能（接続エラー時に最大3回試行）
                max_retries = 3
                last_error: Exception | None = None
                for attempt in range(max_retries):
                    try:
                        response = requests.get(
                            self.wsdl_source,
                            headers=headers,
                            timeout=30,
                            verify=True,
                        )
                        response.raise_for_status()
                        self.tree = etree.fromstring(response.content)
                        self.root = self.tree
                        break
                    except requests.exceptions.ConnectionError as e:
                        last_error = e
                        if attempt < max_retries - 1:
                            print(
                                f"  接続エラー、リトライ中... "
                                f"({attempt + 1}/{max_retries})"
                            )
                            import time

                            time.sleep(1)  # 1秒待機してリトライ
                        else:
                            raise
                else:
                    if last_error:
                        raise last_error
            else:
                print(f"ローカルファイルを読み込み中: {self.wsdl_source}")
                self.tree = etree.parse(self.wsdl_source)
                self.root = self.tree.getroot()

            self.target_namespace = self.root.get("targetNamespace", "")
            print("✓ WSDLファイルの読み込みに成功しました\n")
            return True
        except requests.RequestException as e:
            print(f"エラー: URLからWSDLを取得できませんでした - {e}")
            return False
        except etree.XMLSyntaxError as e:
            print(f"エラー: XMLの解析に失敗しました - {e}")
            return False
        except FileNotFoundError:
            print(f"エラー: ファイルが見つかりません - {self.wsdl_source}")
            return False
        except Exception as e:
            print(f"エラー: WSDLファイルの読み込みに失敗しました - {e}")
            return False

    def _get_elements(self, xpath: str) -> Any:
        """XPathでエレメントを取得"""
        if self.root is None:
            return []
        return self.root.xpath(xpath, namespaces=self.NAMESPACES)

    def parse_services(self) -> List[Dict[str, Any]]:
        """サービス情報を解析"""
        services = []
        for service in self._get_elements("//wsdl:service"):
            service_info = {"name": service.get("name"), "ports": []}

            for port in service.xpath(".//wsdl:port", namespaces=self.NAMESPACES):
                port_info = {
                    "name": port.get("name"),
                    "binding": self._strip_namespace(port.get("binding")),
                    "address": "",
                }

                # SOAP 1.1
                soap_address = port.xpath(".//soap:address", namespaces=self.NAMESPACES)
                if soap_address:
                    port_info["address"] = soap_address[0].get("location", "")

                # SOAP 1.2
                soap12_address = port.xpath(
                    ".//soap12:address", namespaces=self.NAMESPACES
                )
                if soap12_address:
                    port_info["address"] = soap12_address[0].get("location", "")

                service_info["ports"].append(port_info)

            services.append(service_info)

        return services

    def parse_bindings(self) -> List[Dict[str, Any]]:
        """バインディング情報を解析"""
        bindings = []
        for binding in self._get_elements("//wsdl:binding"):
            binding_info = {
                "name": binding.get("name"),
                "type": self._strip_namespace(binding.get("type")),
                "style": "",
                "transport": "",
                "operations": [],
            }

            # SOAP Binding
            soap_binding = binding.xpath(".//soap:binding", namespaces=self.NAMESPACES)
            if soap_binding:
                binding_info["style"] = soap_binding[0].get("style", "document")
                binding_info["transport"] = soap_binding[0].get("transport", "")

            # Operations
            for operation in binding.xpath(
                ".//wsdl:operation", namespaces=self.NAMESPACES
            ):
                op_info = {"name": operation.get("name"), "soapAction": ""}

                soap_op = operation.xpath(
                    ".//soap:operation", namespaces=self.NAMESPACES
                )
                if soap_op:
                    op_info["soapAction"] = soap_op[0].get("soapAction", "")

                binding_info["operations"].append(op_info)

            bindings.append(binding_info)

        return bindings

    def parse_port_types(self) -> List[Dict[str, Any]]:
        """ポートタイプ（インターフェース）を解析"""
        port_types = []
        for port_type in self._get_elements("//wsdl:portType"):
            pt_info = {"name": port_type.get("name"), "operations": []}

            for operation in port_type.xpath(
                ".//wsdl:operation", namespaces=self.NAMESPACES
            ):
                op_info = {
                    "name": operation.get("name"),
                    "documentation": "",
                    "input": "",
                    "output": "",
                }

                # Documentation
                doc = operation.xpath(
                    ".//wsdl:documentation", namespaces=self.NAMESPACES
                )
                if doc and doc[0].text:
                    op_info["documentation"] = doc[0].text.strip()

                # Input
                input_elem = operation.xpath(
                    ".//wsdl:input", namespaces=self.NAMESPACES
                )
                if input_elem:
                    op_info["input"] = self._strip_namespace(
                        input_elem[0].get("message", "")
                    )

                # Output
                output_elem = operation.xpath(
                    ".//wsdl:output", namespaces=self.NAMESPACES
                )
                if output_elem:
                    op_info["output"] = self._strip_namespace(
                        output_elem[0].get("message", "")
                    )

                pt_info["operations"].append(op_info)

            port_types.append(pt_info)

        return port_types

    def parse_messages(self) -> List[Dict[str, Any]]:
        """メッセージ定義を解析"""
        messages = []
        for message in self._get_elements("//wsdl:message"):
            msg_info = {"name": message.get("name"), "parts": []}

            for part in message.xpath(".//wsdl:part", namespaces=self.NAMESPACES):
                part_info = {
                    "name": part.get("name"),
                    "element": self._strip_namespace(part.get("element", "")),
                    "type": self._strip_namespace(part.get("type", "")),
                }
                msg_info["parts"].append(part_info)

            messages.append(msg_info)

        return messages

    def _get_documentation(self, element: etree._Element) -> str:
        """annotation/documentation要素からドキュメント文字列を取得"""
        doc_result = element.xpath(
            "./xsd:annotation/xsd:documentation", namespaces=self.NAMESPACES
        )
        if isinstance(doc_result, list) and len(doc_result) > 0:
            doc_elem = doc_result[0]
            if isinstance(doc_elem, etree._Element) and doc_elem.text:
                return doc_elem.text.strip()
        return ""

    def parse_types(self) -> List[Dict[str, Any]]:
        """データ型定義を解析"""
        types_list = []

        for schema in self._get_elements("//wsdl:types/xsd:schema"):
            # 名前付きComplex Types
            for complex_type in schema.xpath(
                ".//xsd:complexType[@name]", namespaces=self.NAMESPACES
            ):
                type_name = complex_type.get("name")
                type_info = {
                    "name": type_name,
                    "type": "complexType",
                    "documentation": self._get_documentation(complex_type),
                    "elements": [],
                }

                for element in complex_type.xpath(
                    ".//xsd:element", namespaces=self.NAMESPACES
                ):
                    elem_info = {
                        "name": element.get("name"),
                        "type": self._strip_namespace(element.get("type", "")),
                        "minOccurs": element.get("minOccurs", "1"),
                        "maxOccurs": element.get("maxOccurs", "1"),
                        "nillable": element.get("nillable", "false"),
                        "documentation": self._get_documentation(element),
                    }
                    type_info["elements"].append(elem_info)

                types_list.append(type_info)

            # スキーマ直下のElement（complexTypeを内包するものと単純なもの）
            for element in schema.xpath("./xsd:element", namespaces=self.NAMESPACES):
                elem_name = element.get("name")
                if not elem_name:
                    continue

                # 要素のドキュメントを取得
                elem_doc = self._get_documentation(element)

                # 要素内に無名のcomplexTypeがあるかチェック
                inner_complex = element.xpath(
                    "./xsd:complexType", namespaces=self.NAMESPACES
                )
                if inner_complex:
                    # 無名complexTypeを要素名でcomplexTypeとして登録
                    # 無名complexType自体のドキュメントも確認
                    inner_doc = self._get_documentation(inner_complex[0])
                    type_info = {
                        "name": elem_name,
                        "type": "complexType",
                        "documentation": elem_doc or inner_doc,
                        "elements": [],
                    }
                    for inner_elem in inner_complex[0].xpath(
                        ".//xsd:element", namespaces=self.NAMESPACES
                    ):
                        inner_elem_info = {
                            "name": inner_elem.get("name"),
                            "type": self._strip_namespace(inner_elem.get("type", "")),
                            "minOccurs": inner_elem.get("minOccurs", "1"),
                            "maxOccurs": inner_elem.get("maxOccurs", "1"),
                            "nillable": inner_elem.get("nillable", "false"),
                            "documentation": self._get_documentation(inner_elem),
                        }
                        type_info["elements"].append(inner_elem_info)
                    types_list.append(type_info)
                else:
                    # 単純なelement
                    elem_info = {
                        "name": elem_name,
                        "type": "element",
                        "dataType": self._strip_namespace(element.get("type", "")),
                        "documentation": elem_doc,
                    }
                    types_list.append(elem_info)

        return types_list

    def _strip_namespace(self, qname: Optional[str]) -> str:
        """名前空間プレフィックスを削除"""
        if qname and ":" in qname:
            return qname.split(":")[-1]
        return qname or ""

    def parse(self) -> Optional[Dict[str, Any]]:
        """WSDL全体を解析"""
        if not self.load_wsdl():
            return None

        print("WSDLを解析中...")
        data = {
            "target_namespace": self.target_namespace,
            "services": self.parse_services(),
            "bindings": self.parse_bindings(),
            "port_types": self.parse_port_types(),
            "messages": self.parse_messages(),
            "types": self.parse_types(),
        }
        print("✓ 解析完了\n")
        return data


def format_text_output(data: Dict[str, Any]) -> str:
    """テキスト形式で整形して出力"""
    output = []
    output.append("=" * 80)
    output.append("WSDL解析結果")
    output.append("=" * 80)
    output.append(f"\nターゲット名前空間: {data['target_namespace']}\n")

    # サービス情報
    output.append("\n" + "=" * 80)
    output.append("📡 サービス情報")
    output.append("=" * 80)
    for service in data["services"]:
        output.append(f"\n【サービス名】 {service['name']}")
        for port in service["ports"]:
            output.append(f"  ├─ ポート: {port['name']}")
            output.append(f"  │  ├─ バインディング: {port['binding']}")
            output.append(f"  │  └─ エンドポイント: {port['address']}")

    # オペレーション一覧
    output.append("\n" + "=" * 80)
    output.append("🔧 オペレーション一覧")
    output.append("=" * 80)
    for pt in data["port_types"]:
        output.append(f"\n【ポートタイプ】 {pt['name']}")
        for op in pt["operations"]:
            output.append(f"\n  ● {op['name']}")
            if op["documentation"]:
                output.append(f"    説明: {op['documentation']}")
            output.append(f"    入力: {op['input']}")
            output.append(f"    出力: {op['output']}")

            # SOAPActionを探す
            for binding in data["bindings"]:
                if binding["type"] == pt["name"]:
                    for bind_op in binding["operations"]:
                        if bind_op["name"] == op["name"] and bind_op["soapAction"]:
                            output.append(f"    SOAPAction: {bind_op['soapAction']}")

    # メッセージ定義
    output.append("\n" + "=" * 80)
    output.append("📨 メッセージ定義")
    output.append("=" * 80)
    for msg in data["messages"]:
        output.append(f"\n【メッセージ】 {msg['name']}")
        for part in msg["parts"]:
            if part["element"]:
                output.append(f"  ├─ {part['name']} (element: {part['element']})")
            elif part["type"]:
                output.append(f"  ├─ {part['name']} (type: {part['type']})")

    # データ型定義
    if data["types"]:
        output.append("\n" + "=" * 80)
        output.append("📋 データ型定義")
        output.append("=" * 80)
        for dtype in data["types"]:
            if dtype["type"] == "complexType":
                output.append(f"\n【複合型】 {dtype['name']}")
                # 型自体のドキュメント
                if dtype.get("documentation"):
                    output.append(f"    説明: {dtype['documentation']}")
                for elem in dtype["elements"]:
                    occurs = f"[{elem['minOccurs']}..{elem['maxOccurs']}]"
                    nillable = " (nullable)" if elem["nillable"] == "true" else ""
                    doc_text = (
                        f" - {elem['documentation']}"
                        if elem.get("documentation")
                        else ""
                    )
                    output.append(
                        f"  ├─ {elem['name']}: {elem['type']} {occurs}{nillable}{doc_text}"
                    )
            else:
                doc_text = (
                    f"\n    説明: {dtype['documentation']}"
                    if dtype.get("documentation")
                    else ""
                )
                output.append(
                    f"\n【要素】 {dtype['name']} : {dtype['dataType']}{doc_text}"
                )

    output.append("\n" + "=" * 80)
    return "\n".join(output)


def _make_anchor_id(prefix: str, name: str) -> str:
    """HTML用のアンカーIDを生成する（スペースや特殊文字を置換）"""
    # 名前空間プレフィックスがあれば削除し、安全なIDを生成
    safe_name = name.replace(":", "_").replace(" ", "_").replace(".", "_")
    return f"{prefix}_{safe_name}"


def _make_link_if_exists(
    name: str, targets: set, prefix: str, display_text: str | None = None
) -> str:
    """ターゲットが存在する場合はリンクを、存在しない場合はプレーンテキストを返す"""
    # 表示するテキストを決定（display_text > name > 空文字列）
    text = display_text if display_text else (name if name else "")
    if name and name in targets:
        anchor_id = _make_anchor_id(prefix, name)
        return f'<a href="#{anchor_id}" class="ref-link">{text}</a>'
    # リンク対象でなくても、テキストは必ず返す
    return text


def generate_html_output(data: Dict[str, Any]) -> str:
    """HTML形式で出力"""
    # リンク対象となる要素名のセットを事前に収集
    message_names: set = {msg["name"] for msg in data["messages"]}
    type_names: set = set()
    for dtype in data["types"]:
        if dtype.get("name"):
            type_names.add(dtype["name"])

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WSDL解析結果</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            padding: 40px;
        }}
        h1 {{
            color: #667eea;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #764ba2;
            margin-top: 30px;
            padding: 10px;
            background: #f0f0f0;
            border-left: 5px solid #667eea;
        }}
        h3 {{
            color: #555;
            margin-top: 20px;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        .service, .operation, .message, .type {{
            background: #f9f9f9;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            margin: 10px 0;
        }}
        .operation {{
            background: #e8f4f8;
        }}
        .label {{
            font-weight: bold;
            color: #667eea;
        }}
        .value {{
            color: #333;
            margin-left: 10px;
        }}
        .endpoint {{
            word-break: break-all;
            color: #0066cc;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }}
        th, td {{
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #667eea;
            color: white;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 0.85em;
            margin: 2px;
        }}
        .badge-input {{
            background: #4caf50;
            color: white;
        }}
        .badge-output {{
            background: #2196f3;
            color: white;
        }}
        /* リンク用スタイル */
        .ref-link {{
            color: #0066cc;
            text-decoration: none;
            border-bottom: 1px dashed #0066cc;
            transition: all 0.2s ease;
        }}
        .ref-link:hover {{
            color: #004499;
            border-bottom-style: solid;
            background-color: #e8f4f8;
        }}
        /* アンカーターゲットのハイライト */
        :target {{
            animation: highlight 2s ease;
        }}
        @keyframes highlight {{
            0% {{ background-color: #ffeb3b; }}
            100% {{ background-color: transparent; }}
        }}
        /* 目次用スタイル */
        .toc {{
            background: #f5f5f5;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 20px;
        }}
        .toc h3 {{
            margin-top: 0;
            color: #667eea;
        }}
        .toc ul {{
            list-style-type: none;
            padding-left: 0;
        }}
        .toc li {{
            margin: 5px 0;
        }}
        .toc a {{
            color: #667eea;
            text-decoration: none;
        }}
        .toc a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📄 WSDL解析結果</h1>
        <p><span class="label">ターゲット名前空間:</span> <span class="value">{data['target_namespace']}</span></p>

        <div class="toc">
            <h3>📑 目次</h3>
            <ul>
                <li><a href="#section-services">📡 サービス情報</a></li>
                <li><a href="#section-operations">🔧 オペレーション一覧</a></li>
                <li><a href="#section-messages">📨 メッセージ定義</a></li>
                <li><a href="#section-types">📋 データ型定義</a></li>
            </ul>
        </div>
"""

    # サービス情報
    html += '<div class="section" id="section-services"><h2>📡 サービス情報</h2>'
    for service in data["services"]:
        html += f'<div class="service"><h3>{service["name"]}</h3>'
        for port in service["ports"]:
            html += f"""
                <p><span class="label">ポート名:</span> <span class="value">{port["name"]}</span></p>
                <p><span class="label">バインディング:</span> <span class="value">{port["binding"]}</span></p>
                <p><span class="label">エンドポイント:</span> <span class="value endpoint">{port["address"]}</span></p>
            """
        html += "</div>"
    html += "</div>"

    # オペレーション一覧
    html += (
        '<div class="section" id="section-operations"><h2>🔧 オペレーション一覧</h2>'
    )
    for pt in data["port_types"]:
        html += f'<h3>{pt["name"]}</h3>'
        for op in pt["operations"]:
            soap_action = ""
            for binding in data["bindings"]:
                if binding["type"] == pt["name"]:
                    for bind_op in binding["operations"]:
                        if bind_op["name"] == op["name"] and bind_op["soapAction"]:
                            soap_action = bind_op["soapAction"]

            doc_html = (
                f"<p><i>{op['documentation']}</i></p>" if op["documentation"] else ""
            )
            soap_html = (
                f"<p><span class='label'>SOAPAction:</span> <span class='value'>{soap_action}</span></p>"
                if soap_action
                else ""
            )

            # 入力/出力メッセージへのリンクを生成
            input_link = _make_link_if_exists(op["input"], message_names, "msg")
            output_link = _make_link_if_exists(op["output"], message_names, "msg")

            html += f"""
                <div class="operation">
                    <h4>{op["name"]}</h4>
                    {doc_html}
                    <p>
                        <span class="badge badge-input">入力</span> {input_link}
                        <span class="badge badge-output">出力</span> {output_link}
                    </p>
                    {soap_html}
                </div>
            """
    html += "</div>"

    # メッセージ定義
    html += '<div class="section" id="section-messages"><h2>📨 メッセージ定義</h2>'
    for msg in data["messages"]:
        anchor_id = _make_anchor_id("msg", msg["name"])
        html += f'<div class="message" id="{anchor_id}"><h4>{msg["name"]}</h4><table>'
        html += "<tr><th>パラメータ名</th><th>要素/型</th></tr>"
        for part in msg["parts"]:
            if part["element"]:
                # element参照 → データ型へのリンク
                elem_link = _make_link_if_exists(part["element"], type_names, "type")
                elem_or_type = f"element: {elem_link}"
            else:
                # type参照 → データ型へのリンク
                type_link = _make_link_if_exists(part["type"], type_names, "type")
                elem_or_type = f"type: {type_link}"
            html += f'<tr><td>{part["name"]}</td><td>{elem_or_type}</td></tr>'
        html += "</table></div>"
    html += "</div>"

    # データ型定義
    if data["types"]:
        html += '<div class="section" id="section-types"><h2>📋 データ型定義</h2>'
        for dtype in data["types"]:
            if dtype["type"] == "complexType":
                anchor_id = _make_anchor_id("type", dtype["name"])
                html += f'<div class="type" id="{anchor_id}"><h4>{dtype["name"]}</h4>'
                # 型自体のドキュメント
                if dtype.get("documentation"):
                    html += f'<p><i>{dtype["documentation"]}</i></p>'
                html += "<table>"
                html += "<tr><th>フィールド名</th><th>型</th><th>出現回数</th><th>Nullable</th><th>説明</th></tr>"
                for elem in dtype["elements"]:
                    occurs = f"{elem['minOccurs']}..{elem['maxOccurs']}"
                    nillable = "✓" if elem["nillable"] == "true" else ""
                    doc = elem.get("documentation", "")
                    # フィールドの型にもリンクを付ける（他のcomplexTypeを参照している場合）
                    type_link = _make_link_if_exists(elem["type"], type_names, "type")
                    html += f'<tr><td>{elem["name"]}</td><td>{type_link}</td><td>{occurs}</td><td>{nillable}</td><td>{doc}</td></tr>'
                html += "</table></div>"
            else:
                # element型の場合
                anchor_id = _make_anchor_id("type", dtype["name"])
                data_type = dtype.get("dataType", "")
                type_link = _make_link_if_exists(data_type, type_names, "type")
                html += f'<div class="type" id="{anchor_id}"><h4>{dtype["name"]}</h4>'
                # 要素のドキュメント
                if dtype.get("documentation"):
                    html += f'<p><i>{dtype["documentation"]}</i></p>'
                html += f'<p><span class="label">データ型:</span> {type_link}</p></div>'
    html += "</div>"

    html += "</div></body></html>"
    return html


def main():
    parser = argparse.ArgumentParser(
        description="WSDLファイルを解析して読みやすく出力します",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python wsdl_parser.py service.wsdl
  python wsdl_parser.py http://example.com/service?wsdl
  python wsdl_parser.py service.wsdl --output result.html
  python wsdl_parser.py service.wsdl --format html --output result.html
        """,
    )
    parser.add_argument("wsdl", help="WSDLファイルのパスまたはURL")
    parser.add_argument(
        "--output", "-o", help="出力ファイル名（指定しない場合は標準出力）"
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["text", "html"],
        default="text",
        help="出力形式 (text または html、デフォルト: text)",
    )

    args = parser.parse_args()

    # WSDL解析
    wsdl_parser = WSDLParser(args.wsdl)
    data = wsdl_parser.parse()

    if data is None:
        sys.exit(1)

    # 出力形式に応じて整形
    if args.format == "html":
        output_text = generate_html_output(data)
    else:
        output_text = format_text_output(data)

    # 出力
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(output_text, encoding="utf-8")
        print(f"✓ 結果を {args.output} に保存しました")
    else:
        print(output_text)


if __name__ == "__main__":
    main()
