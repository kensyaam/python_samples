#!/usr/bin/env python3
"""
PDF文字列検索ツール

指定した文字列でPDFファイルの内容を一括検索し、結果をCSV形式で出力します。
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import TextIO

import fitz  # PyMuPDF


def get_bookmarks(doc: fitz.Document) -> list[tuple[int, str]]:
    """
    PDFのブックマーク（目次）を取得し、ページ番号とタイトルのリストを返す。

    Args:
        doc: PyMuPDFのドキュメントオブジェクト

    Returns:
        (ページ番号, ブックマークタイトル) のタプルリスト（ページ番号順）
    """
    bookmarks: list[tuple[int, str]] = []
    toc = doc.get_toc()  # [[level, title, page], ...]
    for item in toc:
        level, title, page = item[:3]
        if page >= 1:  # 有効なページ番号のみ
            bookmarks.append((page, title))
    # ページ番号順にソート
    bookmarks.sort(key=lambda x: x[0])
    return bookmarks


def find_nearest_bookmark(bookmarks: list[tuple[int, str]], page_num: int) -> str:
    """
    指定ページに最も近い直前のブックマークを返す。

    Args:
        bookmarks: (ページ番号, タイトル) のリスト
        page_num: 検索対象のページ番号（1始まり）

    Returns:
        直近のブックマークタイトル。なければ空文字列
    """
    nearest = ""
    for bm_page, bm_title in bookmarks:
        if bm_page <= page_num:
            nearest = bm_title
        else:
            break
    return nearest


def extract_context(text: str, search_string: str, ignore_case: bool = False) -> str:
    """
    検索文字列を含む行を抽出する。

    Args:
        text: 検索対象テキスト
        search_string: 検索文字列
        ignore_case: 大文字・小文字を区別しない場合はTrue

    Returns:
        検索文字列を含む行（複数行の場合は改行で連結）
    """
    lines = text.split("\n")
    matched_lines: list[str] = []
    for line in lines:
        if ignore_case:
            if search_string.lower() in line.lower():
                matched_lines.append(line.strip())
        else:
            if search_string in line:
                matched_lines.append(line.strip())
    return " ".join(matched_lines)


def search_pdf(
    pdf_path: Path,
    search_strings: list[str],
    ignore_case: bool = False,
) -> list[dict[str, str | int]]:
    """
    単一のPDFファイルを検索する。

    Args:
        pdf_path: PDFファイルパス
        search_strings: 検索文字列のリスト
        ignore_case: 大文字・小文字を区別しない場合はTrue

    Returns:
        ヒット情報のリスト。各要素は以下のキーを持つ辞書:
        - search_string: 検索文字列
        - page: ページ番号（1始まり）
        - bookmark: 直近のブックマーク
        - context: ヒット箇所を含む文章
    """
    results: list[dict[str, str | int]] = []
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"警告: {pdf_path} を開けませんでした: {e}", file=sys.stderr)
        return results

    bookmarks = get_bookmarks(doc)

    for page_num in range(1, len(doc) + 1):
        page = doc[page_num - 1]
        text = page.get_text()

        for search_string in search_strings:
            # 検索マッチの判定
            # 改行は除去して検索
            if ignore_case:
                match_found = search_string.lower() in text.lower().replace(
                    "\n", " "
                ).replace("\r", " ")
            else:
                match_found = search_string in text.replace("\n", " ").replace(
                    "\r", " "
                )

            if match_found:
                context = extract_context(text, search_string, ignore_case)
                bookmark = find_nearest_bookmark(bookmarks, page_num)
                results.append(
                    {
                        "search_string": search_string,
                        "page": page_num,
                        "bookmark": bookmark,
                        "context": context,
                    }
                )

    doc.close()
    return results


def collect_pdf_files(target: Path) -> list[Path]:
    """
    対象パスからPDFファイルのリストを取得する。

    Args:
        target: PDFファイルまたはディレクトリのパス

    Returns:
        PDFファイルパスのリスト
    """
    if target.is_file():
        if target.suffix.lower() == ".pdf":
            return [target]
        else:
            print(f"警告: {target} はPDFファイルではありません", file=sys.stderr)
            return []
    elif target.is_dir():
        return list(target.rglob("*.pdf"))
    else:
        print(f"エラー: {target} が見つかりません", file=sys.stderr)
        return []


def load_search_strings(file_path: Path) -> list[str]:
    """
    検索文字列リストファイルを読み込む。

    Args:
        file_path: 検索文字列リストファイルのパス

    Returns:
        検索文字列のリスト（空行を除く）
    """
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return [line.strip() for line in lines if line.strip()]


def write_results(
    results: list[tuple[str, list[dict[str, str | int]]]],
    base_path: Path,
    output: TextIO,
    verbose: bool = False,
) -> None:
    """
    検索結果をCSV形式で出力する。

    Args:
        results: (ファイルパス, ヒット情報リスト) のタプルリスト
        base_path: 相対パス計算の基準となるパス
        output: 出力先（ファイルまたはstdout）
        verbose: 詳細出力フラグ
    """
    if verbose:
        fieldnames = [
            "検索文字列",
            "ファイル名",
            "ブックマーク",
            "ページ",
            "ヒット箇所",
        ]
    else:
        fieldnames = ["検索文字列", "ファイル名"]

    writer = csv.DictWriter(output, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
    writer.writeheader()

    for pdf_path_str, hits in results:
        pdf_path = Path(pdf_path_str)
        # 相対パスを計算
        try:
            relative_path = pdf_path.relative_to(base_path)
        except ValueError:
            relative_path = pdf_path

        if verbose:
            # 詳細モード: 各ヒットを個別に出力
            for hit in hits:
                row: dict[str, str | int] = {
                    "検索文字列": hit["search_string"],
                    "ファイル名": str(relative_path),
                    "ブックマーク": hit["bookmark"],
                    "ページ": hit["page"],
                    "ヒット箇所": hit["context"],
                }
                writer.writerow(row)
        else:
            # 通常モード: 検索文字列とファイル名の組み合わせで重複排除
            seen: set[str] = set()
            for hit in hits:
                key = f"{hit['search_string']}|{relative_path}"
                if key not in seen:
                    seen.add(key)
                    row = {
                        "検索文字列": hit["search_string"],
                        "ファイル名": str(relative_path),
                    }
                    writer.writerow(row)


def main() -> None:
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="PDFファイル内を指定文字列で検索し、結果をCSV形式で出力します。"
    )
    parser.add_argument("target", help="検索対象のPDFファイルまたはディレクトリ")
    parser.add_argument("-s", "--search-string", help="検索文字列（単一）")
    parser.add_argument(
        "-f", "--search-file", help="検索文字列リストファイル（改行区切り）"
    )
    parser.add_argument(
        "-i",
        "--ignore-case",
        action="store_true",
        help="大文字・小文字を区別しない",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="詳細出力（ブックマーク、ページ、ヒット箇所）",
    )
    parser.add_argument("-o", "--output", help="出力ファイル（省略時は標準出力）")
    parser.add_argument(
        "-e",
        "--encoding",
        help="出力ファイルのエンコーディング（-oあり時のデフォルト: shift_jis、標準出力時: utf-8）",
    )

    args = parser.parse_args()

    # 検索文字列の取得
    search_strings: list[str] = []
    if args.search_string:
        search_strings.append(args.search_string)
    if args.search_file:
        search_file_path = Path(args.search_file)
        if not search_file_path.exists():
            print(
                f"エラー: 検索文字列ファイル {args.search_file} が見つかりません",
                file=sys.stderr,
            )
            sys.exit(1)
        search_strings.extend(load_search_strings(search_file_path))

    if not search_strings:
        print("エラー: -s または -f で検索文字列を指定してください", file=sys.stderr)
        sys.exit(1)

    # 対象PDFの収集
    target_path = Path(args.target)
    pdf_files = collect_pdf_files(target_path)

    if not pdf_files:
        print("エラー: 検索対象のPDFファイルが見つかりません", file=sys.stderr)
        sys.exit(1)

    # 相対パスの基準を決定
    if target_path.is_dir():
        base_path = target_path
    else:
        base_path = target_path.parent

    # 検索実行
    all_results: list[tuple[str, list[dict[str, str | int]]]] = []
    for pdf_file in pdf_files:
        hits = search_pdf(pdf_file, search_strings, ignore_case=args.ignore_case)
        if hits:
            all_results.append((str(pdf_file), hits))

    # 結果出力
    if args.output:
        # -oオプションあり: デフォルトはShift-JIS
        output_encoding = args.encoding if args.encoding else "windows-31j"
        with open(
            args.output, "w", encoding=output_encoding, errors="replace", newline=""
        ) as f:
            write_results(all_results, base_path, f, verbose=args.verbose)
        print(
            f"結果を {args.output} に出力しました（エンコーディング: {output_encoding}）",
            file=sys.stderr,
        )
    else:
        # 標準出力: デフォルトはUTF-8
        output_encoding = args.encoding if args.encoding else "utf-8"
        import io

        # 標準出力のエンコーディングを指定
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding=output_encoding, newline=""
        )
        write_results(all_results, base_path, sys.stdout, verbose=args.verbose)


if __name__ == "__main__":
    main()
