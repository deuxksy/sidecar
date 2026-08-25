"""시리얼 전송 — write 실패 시 재오픈 (부팅 지연, suspend/resume 후 재인식 대응)."""
import time
import serial


class SerialTransport:
    def __init__(self, target: str, baud: int = 115200, max_backoff: float = 30.0):
        self.target = target
        self.baud = baud
        self.max_backoff = max_backoff
        self._conn: serial.SerialBase | None = None
        self._backoff = 1.0

    def send(self, data: bytes) -> bool:
        try:
            if self._conn is None:
                self._conn = serial.serial_for_url(self.target, self.baud, timeout=1)
                self._backoff = 1.0  # 접속 성공 시 백오프 리셋
            self._conn.write(data)
            return True
        except (serial.SerialException, OSError):
            self.close()
            time.sleep(self._backoff)
            self._backoff = min(self._backoff * 2, self.max_backoff)
            return False

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except OSError:
                pass
            self._conn = None
