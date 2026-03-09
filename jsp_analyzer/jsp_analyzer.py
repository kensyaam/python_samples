"""JSP Analyzer for Modernization.

JSPファイルを解析し、画面構造・データバインディング・ロジック・
外部ファイル依存を可視化するPythonスクリプト。

レガシーシステム（JSP/Spring MVC）からモダンアーキテクチャ
（React/Vue等）への移行調査を支援する。
"""

import argparse
import csv
import io
import logging
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

from bs4 import BeautifulSoup, NavigableString, Tag

# ロガー設定
logger = logging.getLogger(__name__)

# --- アイコン定数 ---
ICON_INCLUDE = "🔗"
ICON_SPRING = "🌱"
ICON_JSTL = "💠"
ICON_DATA = "🧩"
ICON_JAVA = "☕"
ICON_EVENT = "⚡"
ICON_TEXT = "📝"
ICON_MODEL = "📦"
ICON_PATH = "🔴"
ICON_TEST = "❓"
ICON_VAR = "🆔"
ICON_SCRIPT = "📜"
ICON_ERROR = "❌"
ICON_FUNC = "🔧"
ICON_WARNING = "🔥"


def get_display_width(s: str) -> int:
    """文字列の表示幅（半角=1、全角=2）を計算する。"""
    return sum(2 if unicodedata.east_asian_width(c) in "FWA" else 1 for c in s)


def pad_string(s: str, width: int) -> str:
    """指定された表示幅になるよう文字列を右側にスペースでパディングする。"""
    padding = max(0, width - get_display_width(s))
    return s + " " * padding


class MigrationRule(TypedDict, total=False):
    id: str
    name: str
    complexity: str
    target: str
    type: str
    pattern: str
    description: str


class WarningEntry(TypedDict):
    file_path: str
    line_number: int
    rule_id: str
    rule_name: str
    complexity: str
    snippet: str
    raw_snippet: str


# --- 移行支援用の警告ルール（デフォルト） ---
# プロジェクト固有の条件がある場合は、このリストにルールを追加・変更してください。
DEFAULT_MIGRATION_RULES: List[MigrationRule] = [
    {
        "id": "scriptlet",
        "name": "スクリプトレット",
        "complexity": "高",
        "target": "jsp-logic",
        "type": "scriptlet",
        "description": "バックエンドAPI等への移行が必要",
    },
    {
        "id": "jsp_declaration",
        "name": "JSP宣言",
        "complexity": "高",
        "target": "jsp-logic",
        "type": "declaration",
        "description": "バックエンドAPI等への移行が必要",
    },
    {
        "id": "js_event_bind",
        "name": "JSイベントバインド",
        "complexity": "中",
        "target": "js_event",
        "description": "React/Vue等のライフサイクルフックへの移行が必要",
    },
    {
        "id": "js_function",
        "name": "JS関数定義",
        "complexity": "中",
        "target": "js_function",
        "description": "コンポーネント内メソッド等への移行が必要",
    },
    {
        "id": "inline_event",
        "name": "インラインイベント",
        "complexity": "低",
        "target": "inline_event",
        "description": "JSXのイベントハンドラ(onClick等)へ移行",
    },
    {
        "id": "complex_el",
        "name": "複雑なEL式",
        "complexity": "中",
        "target": "el_expression",
        "pattern": r".*[=!<>|&]+.*",
        "description": "Vue/Reactの算出プロパティや条件付きレンダリングへ移行",
    },
    {
        "id": "deprecated_tag",
        "name": "非推奨HTMLタグ",
        "complexity": "低",
        "target": "html_tag",
        "pattern": r"^(font|center|marquee|blink|strike|u)$",
        "description": "CSSでのスタイリングへ移行が必要",
    },
]


class JspPreprocessor:
    """JSP特有の構文をBeautifulSoupがパースできる擬似タグに変換するクラス。

    JSPはHTML/XMLの完全なスーパーセットではないため、
    スクリプトレット・ディレクティブ等を前処理で置換する必要がある。
    """

    def __init__(self) -> None:
        # JSPコメント: <%-- ... --%>
        self.re_comment = re.compile(r"<%--.*?--%>", re.DOTALL)
        # 静的インクルード: <%@ include file="..." %>
        self.re_static_include = re.compile(r'<%@\s*include\s+file="(.*?)"\s*%>')
        # スクリプトレット/式/宣言: <% ... %>, <%= ... %>, <%! ... %>
        self.re_scriptlet = re.compile(r"<%(!?=)?(.*?)%>", re.DOTALL)
        # その他ディレクティブ: <%@ ... %>
        self.re_other_directive = re.compile(r"<%@.*?%>", re.DOTALL)

    def _preserve_newlines(self, match: re.Match[str]) -> str:
        return "\n" * match.group(0).count("\n")

    def preprocess(self, content: str) -> str:
        """JSP特有のタグを擬似タグに置換してパースしやすくする。

        処理順序:
        1. JSPコメントの削除
        2. 静的インクルードを擬似タグに変換
        3. その他のディレクティブを削除（page/taglib等 → 構造破壊防止）
        4. スクリプトレット/式/宣言を擬似タグに変換

        Note:
            手順3を手順4の前に行うことが重要。
            <%@ ... %> もスクリプトレットの正規表現にマッチするため、
            先にディレクティブを除去しておく必要がある。

        Args:
            content: JSPファイルの生テキスト

        Returns:
            前処理済みのHTML文字列
        """
        # 1. JSPコメントを削除 (行番号維持のため改行を残す)
        content = self.re_comment.sub(self._preserve_newlines, content)

        # 2. 静的インクルードを擬似タグに変換
        content = self.re_static_include.sub(
            r'<jsp-static-include file="\1" />', content
        )

        # 3. その他ディレクティブを削除（page/taglib等）
        #    ※ スクリプトレット変換の前に実行すること
        content = self.re_other_directive.sub(self._preserve_newlines, content)

        # 4. スクリプトレット/式/宣言を擬似タグに変換
        content = self.re_scriptlet.sub(self._replace_scriptlet, content)

        return content

    @staticmethod
    def _replace_scriptlet(match: re.Match[str]) -> str:
        """スクリプトレットを擬似タグに置換するコールバック関数。

        Args:
            match: 正規表現のマッチオブジェクト

        Returns:
            擬似タグ文字列
        """
        prefix = match.group(1) or ""
        code = match.group(2)
        if prefix == "=":
            type_name = "expression"
        elif prefix == "!":
            type_name = "declaration"
        else:
            type_name = "scriptlet"
        return f'<jsp-logic type="{type_name}">{code}</jsp-logic>'


class JspAnalyzer:
    """JSPファイルを解析し、構造を可視化するクラス。

    解析対象:
    - HTML構造（タグのネスト関係）
    - Spring Formタグ（form:input, form:select等）
    - JSTL制御構文（c:if, c:forEach等）
    - EL式（${...}）
    - イベントハンドラ（onclick, onchange等）
    - インクルード（静的/動的）
    - スクリプトレット（Javaコード）
    - JavaScriptコード（<script>タグ）
    """

    # Spring Formの重要属性: 小文字キー → 表示用の元名
    # Note: BeautifulSoupのhtml.parserが属性名を小文字化するため、
    #       小文字キーでルックアップし表示は元のキャメルケースを使う
    SPRING_ATTRS: Dict[str, str] = {
        "modelattribute": "modelAttribute",
        "commandname": "commandName",
        "path": "path",
        "items": "items",
        "method": "method",
        "action": "action",
        "cssclass": "cssClass",
        "csserrorclass": "cssErrorClass",
        "enctype": "enctype",
        "value": "value",
        "label": "label",
        "itemvalue": "itemValue",
        "itemlabel": "itemLabel",
        "type": "type",
    }

    # JSTLの重要属性: 小文字キー → 表示用の元名
    JSTL_ATTRS: Dict[str, str] = {
        "test": "test",
        "var": "var",
        "items": "items",
        "value": "value",
        "begin": "begin",
        "end": "end",
        "step": "step",
        "varstatus": "varStatus",
        "url": "url",
        "name": "name",
    }

    # JSTLタグ名の復元マッピング: 小文字タグ名 → 元のキャメルケース表記
    # Note: BeautifulSoupのhtml.parserがタグ名を小文字化するため、
    #       出力時に元のケースに復元する
    JSTL_TAG_NAMES: Dict[str, str] = {
        "c:foreach": "c:forEach",
        "c:setwhen": "c:setWhen",
        "fmt:formatdate": "fmt:formatDate",
        "fmt:formatnumber": "fmt:formatNumber",
        "fmt:parsedate": "fmt:parseDate",
        "fmt:parsenumber": "fmt:parseNumber",
        "fmt:requestencoding": "fmt:requestEncoding",
        "fmt:setbundle": "fmt:setBundle",
        "fmt:setlocale": "fmt:setLocale",
        "fmt:settimezone": "fmt:setTimeZone",
    }

    def __init__(
        self,
        encoding: str = "utf-8",
        no_text: bool = False,
        rules: Optional[List[MigrationRule]] = None,
    ) -> None:
        """JspAnalyzerの初期化。

        Args:
            encoding: JSPファイルの読み込みエンコーディング
            no_text: Trueの場合、EL式を含まない静的テキストを非表示
            rules: カスタム抽出ルール（指定しない場合はデフォルト）
        """
        self.encoding = encoding
        self.no_text = no_text
        self.migration_rules = rules if rules is not None else DEFAULT_MIGRATION_RULES
        self.re_complex_el_cache: Dict[str, re.Pattern] = {}
        for r in self.migration_rules:
            if "pattern" in r and r["pattern"]:
                self.re_complex_el_cache[r["id"]] = re.compile(r["pattern"])

        # 統計情報: { rule_id: count }
        self.global_stats: Dict[str, int] = {r["id"]: 0 for r in self.migration_rules}
        # ファイル別エラー数: { file_path: { rule_id: count } }
        self.file_stats: Dict[str, Dict[str, int]] = {}
        # 警告リスト（CSV出力用）
        self.warning_entries: List[WarningEntry] = []

        self.preprocessor = JspPreprocessor()
        # EL式検出用の正規表現
        self.re_el = re.compile(r"\$\{.*?\}")
        # script内の関数定義検出用の正規表現
        # function name(...), const/let/var name = function(...),
        # const/let/var name = (...) => , const/let/var name = arg =>
        self.re_js_func = re.compile(
            r"(?:"
            r"function\s+([\w$]+)\s*\("
            r"|"
            r"(?:const|let|var)\s+([\w$]+)\s*=\s*"
            r"(?:function\s*\(|\([^)]*\)\s*=>|\w+\s*=>)"
            r")"
        )
        # script内のイベントハンドラ設定検出用の正規表現
        # window.onload = handler, document.onXxx = handler,
        # target.addEventListener('event', handler)
        # グループ: (1)=full prop, (2)=event名, (3)=ハンドラ名,
        #           (4)=target, (5)=event名, (6)=ハンドラ名
        self.re_js_event = re.compile(
            r"(?:"
            r"((?:window|document)\.(on\w+))\s*=\s*([\w$]+)"
            r"|"
            r"(\w+(?:[.(][^)]*\))*(?:\.\w+)*)\."
            r"addEventListener\s*\(\s*['\"]([\w]+)['\"]\s*,\s*([\w$]+)"
            r")"
        )

    def _check_warning(
        self,
        target: str,
        value: str = "",
        type_val: str = "",
        line_number: int = 0,
        raw_snippet: str = "",
    ) -> Optional[MigrationRule]:
        """警告対象かルールベースでチェックする。"""
        for rule in self.migration_rules:
            if rule["target"] != target:
                continue
            if "type" in rule and rule["type"] != type_val:
                continue
            if "pattern" in rule and rule["pattern"]:
                pat = self.re_complex_el_cache.get(rule["id"])
                if pat is None or not pat.search(value):
                    continue
            # カウントアップ
            rule_id = rule["id"]
            self.global_stats[rule_id] += 1
            if (
                getattr(self, "current_file_path", None)
                and self.current_file_path in self.file_stats
            ):
                self.file_stats[self.current_file_path][rule_id] += 1

            # 抽出リストへ追加
            if getattr(self, "current_file_path", None):
                snippet = type_val or value
                # 長いコードは省略表示
                if len(snippet) > 100:
                    snippet = snippet[:97] + "..."
                # 改行除去
                snippet = snippet.replace("\n", " ").replace("\r", "")
                self.warning_entries.append(
                    {
                        "file_path": self.current_file_path,  # type: ignore
                        "line_number": line_number,
                        "rule_id": rule_id,
                        "rule_name": rule.get("name", ""),
                        "complexity": rule.get("complexity", "不明"),
                        "snippet": snippet,
                        "raw_snippet": raw_snippet.strip(),
                    }
                )

            return rule
        return None

    def _format_warning(self, rule: Optional[MigrationRule]) -> str:
        """ルールから警告アイコンのプレフィックスを生成する。"""
        if not rule:
            return ""
        return f"{ICON_WARNING} [{rule['complexity']}] "

    def analyze_file(self, file_path: Path) -> str:
        """JSPファイルを読み込み、解析結果を文字列で返す。

        Args:
            file_path: 解析対象のJSPファイルパス

        Returns:
            解析結果の文字列（ツリー形式）
        """
        try:
            with open(file_path, "r", encoding=self.encoding, errors="replace") as f:
                raw_content = f.read()
        except OSError as e:
            logger.error("ファイル読み込みエラー: %s - %s", file_path, e)
            return f"{ICON_ERROR} Error reading {file_path}: {e}"

        str_path = str(file_path)
        if str_path not in self.file_stats:
            self.file_stats[str_path] = {r["id"]: 0 for r in self.migration_rules}

        # _traverse中に参照できるように現在のファイルパスを保持
        self.current_file_path: Optional[str] = str_path

        preprocessed = self.preprocessor.preprocess(raw_content)
        soup = BeautifulSoup(preprocessed, "html.parser")

        lines: List[str] = [f"=== Analysis Result for: {file_path} ==="]
        self._traverse(soup, lines, 0)

        self.current_file_path = None
        return "\n".join(lines)

    def _traverse(self, node: Any, lines: List[str], indent_level: int) -> None:
        """DOMツリーを再帰的に走査し、解析結果をlines に追加する。

        Args:
            node: 走査対象のBeautifulSoupノード
            lines: 結果を蓄積するリスト
            indent_level: 現在のインデントレベル
        """
        indent = "  " * indent_level

        if isinstance(node, Tag):
            self._process_tag(node, lines, indent, indent_level)
        elif isinstance(node, NavigableString):
            self._process_text(node, lines, indent)

    def _process_tag(
        self, tag: Tag, lines: List[str], indent: str, indent_level: int
    ) -> None:
        """タグノードを処理する。

        Args:
            tag: 処理対象のタグ
            lines: 結果を蓄積するリスト
            indent: インデント文字列
            indent_level: 現在のインデントレベル
        """
        tag_name: str = tag.name

        # --- 擬似タグの処理 ---
        if tag_name == "jsp-static-include":
            file_name = tag.get("file", "")
            lines.append(f"{indent}<{ICON_INCLUDE}Static Include> file='{file_name}'")
            return

        if tag_name == "jsp-logic":
            self._process_jsp_logic(tag, lines, indent)
            return

        # --- HTMLタグの正規表現検出 ---
        rule = self._check_warning(
            target="html_tag",
            value=tag.name,
            line_number=getattr(tag, "sourceline", 0) or 0,
            raw_snippet=self._get_tag_snippet(tag, tag.name),
        )
        tag_warn_mark = self._format_warning(rule) if rule else ""

        # --- タグ情報の組み立て ---
        parts: List[str] = self._build_tag_parts(tag, tag_name)

        # イベントハンドラと属性内のEL式
        self._extract_attr_info(tag, parts, tag_name)

        # タグ名ベースで警告があった場合はプレフィックスに結合
        prefix = indent + tag_warn_mark if tag_warn_mark else indent
        lines.append(f"{prefix}{' '.join(parts)}")

        # scriptタグ内のJavaScript解析
        if tag_name == "script" and not tag.get("src"):
            self._extract_script_info(tag, lines, indent + "  ")

        # 子要素の再帰的な走査
        for child in tag.children:
            self._traverse(child, lines, indent_level + 1)

    def _process_jsp_logic(self, tag: Tag, lines: List[str], indent: str) -> None:
        """JSPロジック擬似タグを処理する。

        Args:
            tag: jsp-logicタグ
            lines: 結果を蓄積するリスト
            indent: インデント文字列
        """
        type_val = tag.get("type", "logic")
        # BeautifulSoupが属性値をリストで返す場合への対応
        type_name = str(type_val[0]) if isinstance(type_val, list) else str(type_val)

        code_inner = tag.get_text()

        # 生コードを元のタグ表記に戻す
        if type_name == "expression":
            raw_snippet = f"<%={code_inner}%>"
        elif type_name == "declaration":
            raw_snippet = f"<%!{code_inner}%>"
        else:
            raw_snippet = f"<%{code_inner}%>"

        rule = self._check_warning(
            target="jsp-logic",
            type_val=type_name,
            line_number=getattr(tag, "sourceline", 0) or 0,
            raw_snippet=raw_snippet,
        )
        warn_mark = self._format_warning(rule)

        # 改行、および、タブ、連続する空白を1つの空白に置換
        code = re.sub(r"[\n\t ]+", " ", raw_snippet).strip()
        # 長いコードは省略表示
        if len(code) > 200:
            code = code[:197] + "..."
        lines.append(
            f"{indent}{warn_mark}[{ICON_JAVA}Java {type_name.capitalize()}]: {code}"
        )

    def _build_tag_parts(self, tag: Tag, tag_name: str) -> List[str]:
        """タグのメイン表示部分を組み立てる。

        Args:
            tag: 対象のタグ
            tag_name: タグ名

        Returns:
            表示パーツのリスト
        """
        parts: List[str] = []
        is_spring = tag_name.startswith("form:")
        is_jstl = tag_name.startswith("c:") or tag_name.startswith("fmt:")
        is_jsp_include = tag_name == "jsp:include"
        is_script = tag_name == "script"

        if is_spring:
            parts.append(f"<{ICON_SPRING}{tag_name}>")
            for lower_key, display_name in self.SPRING_ATTRS.items():
                if tag.has_attr(lower_key):
                    val = tag[lower_key]
                    str_val = " ".join(val) if isinstance(val, list) else str(val)
                    warn_mark, formatted_val = self._process_el_in_attr(
                        tag, tag_name, str_val
                    )
                    icon = self._get_spring_attr_icon(lower_key)
                    parts.append(f"{warn_mark}{icon}{display_name}='{formatted_val}'")

        elif is_jstl:
            # 小文字化されたタグ名を元のキャメルケースに復元
            display_tag_name = self.JSTL_TAG_NAMES.get(tag_name, tag_name)
            parts.append(f"<{ICON_JSTL}{display_tag_name}>")
            for lower_key, display_name in self.JSTL_ATTRS.items():
                if tag.has_attr(lower_key):
                    val = tag[lower_key]
                    str_val = " ".join(val) if isinstance(val, list) else str(val)
                    warn_mark, formatted_val = self._process_el_in_attr(
                        tag, tag_name, str_val
                    )
                    icon = self._get_jstl_attr_icon(lower_key)
                    parts.append(f"{warn_mark}{icon}{display_name}='{formatted_val}'")

        elif is_jsp_include:
            page = tag.get("page", "")
            parts.append(f"<{ICON_INCLUDE}Dynamic Include> page='{page}'")

        elif is_script:
            # scriptタグはロジックとして強調表示
            src = tag.get("src", "")
            if src:
                parts.append(f"<{ICON_SCRIPT}script> src='{src}'")
            else:
                parts.append(f"<{ICON_SCRIPT}script> [inline JavaScript]")

        else:
            parts.append(f"<{tag_name}>")

        return parts

    @staticmethod
    def _get_spring_attr_icon(attr: str) -> str:
        """Spring Form属性に対応するアイコンを返す。

        Args:
            attr: 属性名

        Returns:
            アイコン文字列
        """
        icon_map: Dict[str, str] = {
            "modelattribute": ICON_MODEL,
            "commandname": ICON_MODEL,
            "path": ICON_PATH,
        }
        return icon_map.get(attr, "")

    @staticmethod
    def _get_jstl_attr_icon(attr: str) -> str:
        """JSTL属性に対応するアイコンを返す。

        Args:
            attr: 属性名（小文字）

        Returns:
            アイコン文字列
        """
        icon_map: Dict[str, str] = {
            "test": ICON_TEST,
            "var": ICON_VAR,
        }
        return icon_map.get(attr, "")

    def _get_tag_snippet(self, tag: Tag, tag_name: str) -> str:
        """指定されたタグの生コードスニペットを取得する。

        a, input, form:inputタグの場合は終了タグまで含めた全体を返し、
        それ以外の場合は開始タグのみを返す。
        """
        full_tag = str(tag)
        if tag_name in ("a", "input", "form:input"):
            return full_tag

        match = re.match(r"^<[^>]+>", full_tag)
        if match:
            return match.group(0)
        return full_tag

    def _process_el_in_attr(
        self, tag: Tag, tag_name: str, str_value: str
    ) -> tuple[str, str]:
        """属性値のEL式をチェックし、(警告マーク, アイコンを付与した値) を返す。"""
        if "${" not in str_value:
            return "", str_value

        rule = self._check_warning(
            target="el_expression",
            value=str_value,
            line_number=getattr(tag, "sourceline", 0) or 0,
            raw_snippet=self._get_tag_snippet(tag, tag_name),
        )
        warn_mark = self._format_warning(rule)

        # EL式のアイコンを値の先頭に付与
        return warn_mark, f"{ICON_DATA}{str_value}"

    def _extract_attr_info(self, tag: Tag, parts: List[str], tag_name: str) -> None:
        """タグの属性からイベントハンドラ・EL式・href等を抽出する。

        Args:
            tag: 対象のタグ
            parts: 表示パーツのリスト（追記先）
            tag_name: タグ名
        """
        # 処理済み属性セット（小文字化済み）
        spring_keys = set(self.SPRING_ATTRS.keys())
        jstl_keys = set(self.JSTL_ATTRS.keys())

        for attr, value in tag.attrs.items():
            # 既にSpring/JSTLで処理済みの属性はスキップ
            if tag_name.startswith("form:") and attr in spring_keys:
                continue
            if (
                tag_name.startswith("c:") or tag_name.startswith("fmt:")
            ) and attr in jstl_keys:
                continue

            # 値がリストの場合は文字列に結合（class属性等）
            str_value = " ".join(value) if isinstance(value, list) else str(value)

            # イベントハンドラ
            if attr.startswith("on"):
                rule = self._check_warning(
                    target="inline_event",
                    value=f"{attr}='{str_value}'",
                    line_number=getattr(tag, "sourceline", 0) or 0,
                    raw_snippet=self._get_tag_snippet(tag, tag_name),
                )
                warn_mark = self._format_warning(rule)
                parts.append(f"{warn_mark}{ICON_EVENT}{attr}='{str_value}'")
            # 属性内のEL式
            elif "${" in str_value:
                warn_mark, formatted_val = self._process_el_in_attr(
                    tag, tag_name, str_value
                )
                parts.append(f"{warn_mark}{attr}='{formatted_val}'")
            # href属性（aタグ）
            elif attr == "href" and tag_name == "a":
                parts.append(f"href='{str_value}'")
            # 標準HTMLタグのtype/value/name属性
            elif attr in ("type", "value", "name") and not (
                tag_name.startswith("form:")
                or tag_name.startswith("c:")
                or tag_name.startswith("fmt:")
            ):
                if attr == "name":
                    parts.append(f"{ICON_PATH}{attr}='{str_value}'")
                else:
                    parts.append(f"{attr}='{str_value}'")

    def _extract_script_info(self, tag: Tag, lines: List[str], indent: str) -> None:
        """scriptタグ内のJavaScriptから関数定義・イベントハンドラ設定を抽出する。

        Args:
            tag: scriptタグ
            lines: 結果を蓄積するリスト
            indent: インデント文字列
        """
        script_text = tag.get_text()
        if not script_text.strip():
            return

        base_line = getattr(tag, "sourceline", 0) or 0

        # 関数定義の抽出
        func_entries: List[tuple[str, str, int]] = []
        for match in self.re_js_func.finditer(script_text):
            # group(1): function宣言形式, group(2): 変数代入形式
            name = match.group(1) or match.group(2)
            if name and not any(n == name for n, _, _ in func_entries):
                # match.start() までの改行を数えて実際の行番号を計算
                line_offset = script_text[: match.start()].count("\n")
                actual_line = base_line + line_offset if base_line else 0
                func_entries.append((name, match.group(0), actual_line))

        for func_name, raw_code, line_num in func_entries:
            rule = self._check_warning(
                target="js_function",
                value=func_name,
                line_number=line_num,
                raw_snippet=raw_code,
            )
            warn_mark = self._format_warning(rule)
            lines.append(f"{indent}{warn_mark}{ICON_FUNC} [Function]: {func_name}")

        # イベントハンドラ設定の抽出
        event_entries: List[tuple[str, str, int]] = []
        for match in self.re_js_event.finditer(script_text):
            if match.group(1):
                # window.onload = handler 形式
                binding = match.group(1)
                handler_name = match.group(3)
            else:
                # target.addEventListener('event', handler) 形式
                target = match.group(4)
                event = match.group(5)
                binding = f"{target}.on('{event}')"
                handler_name = match.group(6)

            # function/匿名関数の場合は (anonymous) と表示
            if handler_name == "function":
                handler_name = "(anonymous)"

            entry = f"{binding} → {handler_name}"
            if not any(e == entry for e, _, _ in event_entries):
                line_offset = script_text[: match.start()].count("\n")
                actual_line = base_line + line_offset if base_line else 0
                event_entries.append((entry, match.group(0), actual_line))

        for handler, raw_code, line_num in event_entries:
            rule = self._check_warning(
                target="js_event",
                value=handler,
                line_number=line_num,
                raw_snippet=raw_code,
            )
            warn_mark = self._format_warning(rule)
            lines.append(f"{indent}{warn_mark}{ICON_EVENT} [Event Binding]: {handler}")

    def _process_text(
        self, node: NavigableString, lines: List[str], indent: str
    ) -> None:
        """テキストノードを処理する。

        Args:
            node: テキストノード
            lines: 結果を蓄積するリスト
            indent: インデント文字列
        """
        text = node.strip()
        if not text:
            return

        # EL式の抽出
        el_matches: List[str] = self.re_el.findall(text)
        if el_matches:
            el_text = " ".join(el_matches)
            parent = node.parent
            line_num = getattr(parent, "sourceline", 0) if parent else 0

            raw_snippet = el_text
            if parent:
                parent_name = getattr(parent, "name", "")
                if parent_name:
                    # 親タグがある場合は、そのタグ自体のスニペットを取得する
                    raw_snippet = self._get_tag_snippet(parent, parent_name)

            rule = self._check_warning(
                target="el_expression",
                value=el_text,
                line_number=line_num or 0,
                raw_snippet=raw_snippet,
            )
            warn_mark = self._format_warning(rule)
            # lines.append(f"{indent}{warn_mark}{ICON_DATA} [Data]: {el_text}")
            lines.append(f"{indent}{warn_mark}{ICON_DATA} {el_text}")

        # 静的テキスト（--no-text オプション時は非表示）
        if not self.no_text:
            clean_text = self.re_el.sub("", text).strip()
            if clean_text:
                # 長いテキストは省略表示
                if len(clean_text) > 200:
                    clean_text = clean_text[:197] + "..."
                lines.append(f"{indent}{ICON_TEXT} {clean_text}")

    def print_summary(self) -> None:
        """解析結果のサマリー（統計情報）をコンソールに出力する。"""
        print("\n" + "=" * 60)
        print("【移行タスク サマリーレポート】")
        print("=" * 60)

        total_warnings = sum(self.global_stats.values())
        print(f"対象ファイル数: {len(self.file_stats)}")
        print(f"要注意箇所(全体): {total_warnings} 件\n")

        print("[ルール別 検出数 内訳]")

        # 名前の最大表示幅を計算
        max_name_width = max(
            get_display_width(r.get("name", "")) for r in self.migration_rules
        )

        # 難易度が高い順に並べるためのマッピング
        comp_order = {"高": 1, "中": 2, "低": 3}
        sorted_rules = sorted(
            self.migration_rules,
            key=lambda r: (comp_order.get(r.get("complexity", "高"), 99), r["id"]),
        )
        for r in sorted_rules:
            count = self.global_stats.get(r["id"], 0)
            name_padded = pad_string(r.get("name", ""), max_name_width)
            msg = (
                f"  {name_padded} (難易度: {r.get('complexity', '不明')}): {count:>4}件"
            )
            print(f"{msg} - {r.get('description', '')}")

        print("\n[手直しが多いファイル Top 5]")
        # ファイルごとに警告数を合計
        file_warn_counts = [
            (fpath, sum(counts.values())) for fpath, counts in self.file_stats.items()
        ]
        # 降順でソート
        top_files = sorted(file_warn_counts, key=lambda x: x[1], reverse=True)[:5]
        for fpath, w_count in top_files:
            if w_count > 0:
                print(f"  {w_count:>4}件 : {fpath}")
        print("=" * 60 + "\n")

    def export_csv(self, output_path: Path) -> None:
        """解析で抽出された手作業移行必須リストをCSVとして出力する。"""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            # ヘッダー行
            writer.writerow(
                [
                    "対象ファイル",
                    "行番号",
                    "難易度",
                    "種類",
                    "該当コード/属性値（スニペット）",
                    "生コード",
                ]
            )

            # # 内容行（難易度順 > ファイルパス順）
            # comp_order = {"高": 1, "中": 2, "低": 3}
            # sorted_entries = sorted(
            #     self.warning_entries,
            #     key=lambda x: (
            #         comp_order.get(x["complexity"], 99),
            #         x["file_path"],
            #         x.get("line_number", 0),
            #     ),
            # )
            sorted_entries = self.warning_entries
            for entry in sorted_entries:
                writer.writerow(
                    [
                        entry["file_path"],
                        entry.get("line_number", ""),
                        entry["complexity"],
                        entry["rule_name"],
                        entry["snippet"],
                        entry.get("raw_snippet", ""),
                    ]
                )


def find_jsp_files(input_dir: Path) -> List[Path]:
    """指定ディレクトリ配下の全JSPファイルを再帰的に検索する。

    Args:
        input_dir: 検索対象のルートディレクトリ

    Returns:
        見つかったJSPファイルのパスリスト（ソート済み）
    """
    return sorted(input_dir.rglob("*.jsp"))


def save_result(
    result: str,
    jsp_file: Path,
    input_path: Path,
    output_path: Path,
) -> Path:
    """解析結果をファイルに保存する。

    入力ディレクトリの階層構造を維持し、.jsp.txt として保存する。

    Args:
        result: 解析結果の文字列
        jsp_file: 元のJSPファイルパス
        input_path: 入力ルートディレクトリ
        output_path: 出力ルートディレクトリ

    Returns:
        保存先のファイルパス
    """
    relative_path = jsp_file.relative_to(input_path)
    target_file = output_path / relative_path.with_suffix(".jsp.txt")
    target_file.parent.mkdir(parents=True, exist_ok=True)

    with open(target_file, "w", encoding="utf-8") as f:
        f.write(result)

    return target_file


def main() -> None:
    """メインエントリポイント。コマンドライン引数を解析し、JSP解析を実行する。"""
    # Windowsでの文字化け対策（絵文字出力用）
    if sys.platform == "win32" and isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="JSP Analyzer for Modernization — "
        "JSPファイルを解析し、画面構造・データバインディング・"
        "ロジック・外部ファイル依存を可視化します。"
    )
    parser.add_argument(
        "input_dir", type=str, nargs="?", help="解析対象のディレクトリパス"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="解析結果の出力先ディレクトリ（指定時は .jsp.txt を生成）",
    )
    parser.add_argument(
        "--encoding",
        type=str,
        default="utf-8",
        help="JSPファイルの文字エンコーディング（デフォルト: utf-8）",
    )
    parser.add_argument(
        "--no-text",
        action="store_true",
        help="EL式を含まない静的テキスト（ラベル等）を非表示にする",
    )

    parser.add_argument(
        "--show-rules",
        action="store_true",
        help="現在の抽出ルール（移行警告ルール）を表示して終了する",
    )

    parser.add_argument(
        "--csv-output",
        type=str,
        default=None,
        help="手作業移行必須リストの一覧をCSV形式で出力するファイルパス（例: reports.csv）",
    )

    args = parser.parse_args()

    if args.show_rules:
        print("=== 現在の移行支援警告ルール ===")
        for r in DEFAULT_MIGRATION_RULES:
            print(f"- {r.get('name')} (難易度: {r.get('complexity')})")
            print(f"  対象: {r.get('target')}")
            if "type" in r:
                print(f"  種類: {r.get('type')}")
            if "pattern" in r:
                print(f"  パターン: {r.get('pattern')}")
            print(f"  説明: {r.get('description')}\n")
        print(
            "※ ルールをカスタマイズしたい場合は、スクリプト先頭の DEFAULT_MIGRATION_RULES を直接編集するか、"
        )
        print(
            "   JspAnalyzerクラスのコンストラクタにカスタマイズルールのリストを渡してください。"
        )
        sys.exit(0)

    input_path = Path(args.input_dir)
    output_path: Optional[Path] = Path(args.output_dir) if args.output_dir else None

    if not input_path.exists():
        print(f"Error: 入力ディレクトリ '{input_path}' が見つかりません。")
        sys.exit(1)

    if not input_path.is_dir():
        print(f"Error: '{input_path}' はディレクトリではありません。")
        sys.exit(1)

    analyzer = JspAnalyzer(encoding=args.encoding, no_text=args.no_text)

    # 再帰的にJSPファイルを検索
    jsp_files = find_jsp_files(input_path)
    print(f"Found {len(jsp_files)} JSP file(s).\n")

    if not jsp_files:
        print("解析対象のJSPファイルが見つかりませんでした。")
        return

    for jsp_file in jsp_files:
        result = analyzer.analyze_file(jsp_file)

        # コンソール出力
        print(result)
        print("-" * 60)

        # ファイル出力（--output-dir指定時）
        if output_path:
            target_file = save_result(result, jsp_file, input_path, output_path)
            print(f"  -> Saved to: {target_file}")

    # すべてのファイル解析後、サマリーを出力
    analyzer.print_summary()

    # CSV出力（--csv-output指定時）
    if args.csv_output:
        csv_path = Path(args.csv_output)
        analyzer.export_csv(csv_path)
        print(f"-> 移行必須リスト（CSV）を保存しました: {csv_path}")


if __name__ == "__main__":
    main()
