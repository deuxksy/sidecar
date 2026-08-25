"""확정 프로토콜 golden — layout.json·인코더·CRC prepend가 함께 회귀하는지 감지.

프로토콜 확정(2026-08-25, 역컴파일+실기+커뮤니티 3-way)의 스냅샷.
golden 재생성: scripts/make_golden.py
"""
import struct
import zlib
from pathlib import Path

from am02_subscreen.protocol import build_frame, load_layout

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = Path(__file__).parent / "golden" / "state.bin"
FIXED_METRICS = {
    "cpu_temp": 44.0,
    "gpu_temp": -5.0,  # 음수 온도 — signed 패킹 회귀 포함
    "time_year": 2026, "time_month": 8, "time_day": 25, "time_dow": 2,  # 2026-08-25 화요일
    "time_hour": 7, "time_minute": 7, "time_second": 0,
}


def test_encoded_frame_matches_golden():
    enc = load_layout(ROOT / "layout.json")
    assert build_frame(enc.encode(FIXED_METRICS)) == GOLDEN.read_bytes()


def test_golden_frame_shape():
    frame = GOLDEN.read_bytes()
    assert len(frame) == 253
    assert frame[4] == 0x02  # payload[0] = cmd 2 (상태 갱신)
    assert frame[0:4] == struct.pack("<I", zlib.crc32(frame[4:]) & 0xFFFFFFFF)
    # 온도 필드 @41(=45 payload+4)/@57 — signed int LE
    assert struct.unpack_from("<i", frame, 4 + 41)[0] == 44
    assert struct.unpack_from("<i", frame, 4 + 57)[0] == -5
    # 시간 블록 @117 is24Hour=1, @118 style=0(고정), @119 year u16 LE
    assert frame[4 + 117] == 1
    assert frame[4 + 118] == 0
    assert struct.unpack_from("<H", frame, 4 + 119)[0] == 2026
