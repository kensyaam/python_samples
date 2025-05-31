import inspect
import logging

import requests


def detect_log_level(log_line: str) -> str:
    """
    ログからログレベルを取得.
    Args:
        log_line (str): A single line from the log.
    Returns:
        str: The detected log level (e.g., "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL").
    """
    # log_lineの先頭は"[<TIMESTAMP>] [<LOG_LEVEL>]"の形式であることを前提とする
    if log_line.startswith("[") and "]" in log_line:
        level_start = log_line.index("] [") + 3  # "] ["の後から始まる
        level_end = log_line.index("]", level_start)
        return log_line[level_start:level_end].upper()
    return "UNKNOWN"


def check_log(log_lines: list, level: str, text: str) -> str | None:
    """
    Check if a specific log entry exists in the log lines.
    Args:
        log_lines (list): List of log lines to search.
        level (str): Expected log level (e.g., "INFO", "ERROR").
        text (str): Text to search for in the log line.
    Returns:
        str: The actual log if found, otherwise None.
    """
    actual_line = None
    actual_level = "UNKNOWN"

    for line in log_lines:
        if text in line:
            actual_level = detect_log_level(line)

            # ログ本文を抽出
            log_level_str = f"[{actual_level}]"
            log_level_start = line.index(log_level_str)
            msg_start = log_level_start + len(log_level_str)
            log_msg = line[msg_start:]
            actual_line = log_msg

            assert (
                actual_level == level
            ), f"Expected log level '{level}' but found '{actual_level}' in line: {line}"
            break

    return actual_line


def test_log_levels(runner):
    """
    Test that the log levels are correctly detected in the Azure Functions logs.
    """
    runner.write_log_message(f"==== テスト関数 [{inspect.currentframe().f_code.co_name}] Start ====")

    # リクエスト送信など
    response = requests.get("http://localhost:7071/api/http_trigger")
    assert response.status_code == 200

    log_lines = runner.get_and_clear_log_lines()
    check_log(log_lines, "DEBUG", "DEBUG level log")


def test_log_levels_2(runner):
    """
    Test that the log levels are correctly detected in the Azure Functions logs.
    """
    runner.write_log_message(f"==== テスト関数 [{inspect.currentframe().f_code.co_name}] Start ====")

    # リクエスト送信など
    response = requests.get("http://localhost:7071/api/http_trigger")
    assert response.status_code == 200

    log_lines = runner.get_and_clear_log_lines()
    check_log(log_lines, "INFO", "INFO level log")
    check_log(log_lines, "INFO", "WARNING level log")
    check_log(log_lines, "ERROR", "ERROR level log")
