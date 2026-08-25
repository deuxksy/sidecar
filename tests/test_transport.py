"""loop:// 가상 시리얼로 송신 성공/재연결 검증 — 하드웨어 불필요."""
from am02_subscreen.transport import SerialTransport


def test_send_recovers_after_write_failure(monkeypatch):
    # suspend/resume 등으로 기존 연결의 write가 죽는 경우 — close 후 재오픈으로 자가 복구
    monkeypatch.setattr("am02_subscreen.transport.time.sleep", lambda s: None)
    tx = SerialTransport("loop://")
    assert tx.send(b"\x01") is True

    def _raise(data):
        raise OSError("device disconnected")

    monkeypatch.setattr(tx._conn, "write", _raise)
    assert tx.send(b"\x01") is False
    assert tx._conn is None  # 죽은 연결은 폐기
    assert tx.send(b"\x01") is True  # 다음 send에서 재오픈
    assert tx._backoff == 1.0  # 재접속 성공으로 백오프 리셋
    tx.close()


def test_send_succeeds_on_valid_target():
    tx = SerialTransport("loop://")
    assert tx.send(b"\xAA\x01") is True
    tx.close()


def test_send_returns_false_and_retries_on_missing_device():
    tx = SerialTransport("/dev/ttyAM02-없는포트")
    # send는 내부 backoff sleep 후 False 반환 — 첫 재시도 1초만 대기
    assert tx.send(b"\x00") is False
    assert tx._conn is None  # 닫힌 상태로 대기
    tx.close()
