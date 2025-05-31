import os
import subprocess
import threading
import time
from collections import deque
from datetime import datetime, timezone

# 起動完了を確認するためのログ
# STARTED_LOG = "Host started"
STARTED_LOG = "Worker process started and initialized"


class FuncRunner:
    """
    Azure Functions のランタイムを起動し、ログを取得するためのクラス
    """

    def __init__(self, buffer_size=1000, log_dir="logs"):
        self.proc = None
        self._log_buffer = deque(maxlen=buffer_size)
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None

        # ログファイル名の生成
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self._log_path = os.path.join(log_dir, f"{timestamp}_func.log")
        self._log_file = open(self._log_path, "a", encoding="utf-8")

    def start(self) -> None:
        """
        Azure Functionsランタイムを起動する
        Raises:
            RuntimeError: 既にプロセスが起動している場合
            TimeoutError: 起動完了までに時間がかかりすぎた場合
        """
        if self.proc:
            raise RuntimeError("Process already started")

        print("Starting Azure Functions Runtime ...")

        self._log_buffer.clear()
        self._stop_event.clear()

        self.proc = subprocess.Popen(
            ["func", "start", "--verbose"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self._thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._thread.start()

        # 起動完了を確認
        for _ in range(300):
            if any(STARTED_LOG in line for line in self._log_buffer):
                print("Azure Functions Runtime started.")
                time.sleep(0.5)  # 少し待ってから返す
                return
            time.sleep(0.1)
        raise TimeoutError("Azure Functions host did not start in time.")

    def _read_stdout(self) -> None:
        """
        標準出力を読み取り、ログバッファに追加する
        """
        for line in self.proc.stdout:
            with self._lock:
                self._log_buffer.append(line)

                # ログファイルに書き込む
                self._log_file.write(line)
                self._log_file.flush()
            if self._stop_event.is_set():
                break

    def stop(self) -> None:
        """
        Azure Functionsランタイムを停止する
        """
        if self.proc:
            self._stop_event.set()
            self.proc.terminate()
            self.proc.wait()
            self.proc = None
        if self._thread:
            self._thread.join()
            self._thread = None
        self._log_file.close()
        print("Azure Functions Runtime stopped.")

    def get_log_lines(self) -> list:
        """
        現在のログバッファの内容を取得する
        Returns:
            list: ログの行のリスト
        """
        with self._lock:
            return list(self._log_buffer)

    def get_and_clear_log_lines(self) -> list:
        """
        現在のログバッファの内容を取得し、バッファをクリアする
        Returns:
            list: ログの行のリスト
        """
        with self._lock:
            lines = list(self._log_buffer)
            self._log_buffer.clear()
            return lines

    def write_log_message(self, message: str) -> None:
        """
        任意のメッセージをログファイルに書き込む（例：テスト開始の印）
        """
        # タイムスタンプはUTCで出力
        now_utc = datetime.now(timezone.utc)
        milliseconds = now_utc.microsecond // 1000
        timestamped_message = (
            f"[{now_utc.strftime('%Y-%m-%dT%H:%M:%S')}.{milliseconds:03d}Z] {message}\n"
        )
        with self._lock:
            self._log_file.write(timestamped_message)
            self._log_file.flush()
