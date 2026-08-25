"""run()이 수집→인코딩→전송 후 stop 신호로 종료하는지 검증 (loop:// + monkeypatch)."""
import threading
from pathlib import Path

from am02_subscreen import main as main_mod
from am02_subscreen.main import run
from am02_subscreen.protocol import FrameEncoder, load_layout

LAYOUT = Path(__file__).parents[1] / "layout.json"
MOCK_METRICS = {
    "cpu_temp": 44.0, "gpu_temp": 42.0, "unix_ts": 0.0,
    "time_year": 2026, "time_month": 8, "time_day": 25, "time_dow": 2,
    "time_hour": 7, "time_minute": 7, "time_second": 0,
}


def test_run_sends_one_frame_then_stops(monkeypatch):
    monkeypatch.setattr(main_mod, "collect", lambda: dict(MOCK_METRICS))

    stop = threading.Event()
    orig_send = main_mod.SerialTransport.send
    captured = {}

    def send_once_then_stop(self, data):  # 1회 송신 즉시 종료 — 결정적 테스트
        captured["frame"] = data
        result = orig_send(self, data)
        stop.set()
        return result

    monkeypatch.setattr(main_mod.SerialTransport, "send", send_once_then_stop)

    sent = run("loop://", load_layout(LAYOUT), poll=0.01, stop=stop)

    assert sent == 1
    # wire 전체 = CRC prepend 4B + payload 249B — main이 build_frame을 거치는지
    assert len(captured["frame"]) == 253


def test_run_skips_cycle_on_transient_collect_failure(monkeypatch):
    # suspend/resume·udev 재열거 시 collect()가 FileNotFoundError를 던져도
    # 데몬은 죽지 않고 해당 사이클만 건너뛴 뒤 정상 송신해야 함
    calls = {"n": 0}

    def flaky_collect():
        calls["n"] += 1
        if calls["n"] == 1:
            raise FileNotFoundError("/sys/class/hwmon/hwmon3/temp1_input")
        return dict(MOCK_METRICS)

    monkeypatch.setattr(main_mod, "collect", flaky_collect)

    stop = threading.Event()
    orig_send = main_mod.SerialTransport.send

    def send_once_then_stop(self, data):
        result = orig_send(self, data)
        stop.set()
        return result

    monkeypatch.setattr(main_mod.SerialTransport, "send", send_once_then_stop)

    sent = run("loop://", load_layout(LAYOUT), poll=0.01, stop=stop)

    assert sent == 1  # 실패 사이클 건너뛴 뒤 1회 송신 — OSError는 치명적이지 않음


def test_cli_parses_target_and_layout_option():
    args = main_mod.build_parser().parse_args(["loop://", "--layout", str(LAYOUT)])
    assert args.target == "loop://"
    assert args.layout == LAYOUT


def test_default_layout_points_at_repo_layout():
    # 브리프 샘플(parent.parent)은 src/layout.json — 실제 파일은 저장소 루트에 있음
    assert main_mod.DEFAULT_LAYOUT == LAYOUT
    assert LAYOUT.exists()


def test_main_wires_cli_and_exits_zero(monkeypatch):
    captured = {}

    def fake_run(target, encoder, stop):
        captured["target"] = target
        captured["encoder"] = encoder
        captured["stop"] = stop
        return 0

    monkeypatch.setattr(main_mod, "run", fake_run)
    monkeypatch.setattr(main_mod.signal, "signal", lambda *a: None)

    rc = main_mod.main(["loop://", "--layout", str(LAYOUT)])

    assert rc == 0  # 정상 종료 exit code
    assert captured["target"] == "loop://"
    assert isinstance(captured["encoder"], FrameEncoder)
    assert isinstance(captured["stop"], threading.Event)
