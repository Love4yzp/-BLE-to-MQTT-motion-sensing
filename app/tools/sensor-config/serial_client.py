from __future__ import annotations

import queue
import threading
import time
from typing import Callable, Optional, Tuple

import serial


class SerialClient:
    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        read_timeout: float = 0.1,
        on_line: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.read_timeout = read_timeout
        self.on_line = on_line

        self._serial: Optional[serial.Serial] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._queue: "queue.Queue[str]" = queue.Queue(maxsize=1000)
        self._lock = threading.Lock()

    def connect(self) -> None:
        if self._serial is not None:
            return
        self._serial = serial.Serial(
            self.port,
            self.baudrate,
            timeout=self.read_timeout,
        )
        self._stop_event.clear()
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()

    def disconnect(self) -> None:
        self._stop_event.set()
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=1.0)
        self._reader_thread = None
        if self._serial:
            try:
                self._serial.close()
            finally:
                self._serial = None

    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def send_command(
        self,
        command: str,
        timeout: float = 2.0,
    ) -> Tuple[list[str], bool]:
        if not self.is_connected() or self._serial is None:
            raise RuntimeError("Serial not connected")

        with self._lock:
            self._drain_queue()
            self._serial.write((command + "\r\n").encode("utf-8"))
            lines: list[str] = []
            ok_seen = False
            deadline = time.monotonic() + timeout

            while time.monotonic() < deadline:
                remaining = deadline - time.monotonic()
                try:
                    line = self._queue.get(timeout=remaining)
                except queue.Empty:
                    break
                lines.append(line)
                upper = line.strip().upper()
                if upper.startswith("OK") or upper.startswith("ERROR"):
                    ok_seen = True
                    break

            return lines, ok_seen

    def _reader_loop(self) -> None:
        while not self._stop_event.is_set():
            if self._serial is None:
                break
            try:
                raw = self._serial.readline()
            except serial.SerialException:
                break
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            if self.on_line:
                self.on_line(line)

            try:
                self._queue.put_nowait(line)
            except queue.Full:
                try:
                    self._queue.get_nowait()  # Drop oldest
                    self._queue.put_nowait(line)
                except queue.Empty:
                    pass

    def _drain_queue(self) -> None:
        try:
            while True:
                self._queue.get_nowait()
        except queue.Empty:
            return
