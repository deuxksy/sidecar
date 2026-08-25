"""데몬 진입점 — 수집→인코딩→전송 루프. SIGTERM/SIGINT로 정상 종료."""
import signal
import threading
from argparse import ArgumentParser
from pathlib import Path

from .protocol import FrameEncoder, load_layout
from .sensors import collect
from .transport import SerialTransport

DEFAULT_PORT = "/dev/ttyS0"
# 브리프 샘플(parent.parent)은 src/layout.json을 가리켰으나 실제 파일은 저장소 루트에 있음
DEFAULT_LAYOUT = Path(__file__).resolve().parents[2] / "layout.json"


def run(target: str, encoder: FrameEncoder, poll: float = 1.0,
        stop: threading.Event | None = None) -> int:
    """수집→인코딩→전송을 stop 신호까지 반복. 전송 성공 프레임 수 반환."""
    if stop is None:
        stop = threading.Event()
    tx = SerialTransport(target)
    sent = 0
    while not stop.is_set():
        # 일시적 센서 실패(suspend/resume·udev 재열거의 FileNotFoundError/EIO)는
        # 해당 사이클만 건너뛴다 — 전송은 transport가 자체 처리하므로 collect만 방어
        try:
            reading = collect()
        except OSError:
            reading = None
        if reading is not None and tx.send(encoder.encode(reading)):
            sent += 1
        stop.wait(poll)  # sleep 대신: stop.set()에 즉시 반응
    tx.close()
    return sent


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="am02-subscreend",
        description="AM02 서브스크린 데몬 — CPU/GPU 온도를 전면 디스플레이로 전송")
    parser.add_argument("target", nargs="?", default=DEFAULT_PORT,
                        help="시리얼 포트 또는 pyserial URL (기본: %(default)s)")
    parser.add_argument("--layout", type=Path, default=DEFAULT_LAYOUT,
                        help="레이아웃 JSON 경로 (기본: %(default)s)")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 진입점 — 시그널을 stop 이벤트에 연결 후 run() 실행. 0이면 정상 종료."""
    args = build_parser().parse_args(argv)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    run(args.target, load_layout(args.layout), stop=stop)
    return 0


if __name__ == "__main__":
    main()
