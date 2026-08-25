"""프레임 인코더 — 레이아웃 데이터(layout.json)만으로 프로토콜을 표현한다.

캡처로 프로토콜이 확정되면 코드 변경 없이 layout.json만 교체하면 된다.
"""
import json
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

PAYLOAD_SIZE = 249  # wire 확정: [CRC32 4B LE][payload 249B] = 253B (실기 2026-08-25)


@dataclass(frozen=True)
class FieldSpec:
    name: str      # collect()가 반환하는 metrics 키
    offset: int    # 프레임 내 바이트 오프셋
    size: int      # 바이트 수
    scale: float   # 값 × scale → 변환 후 패킹 (온도 0.1°C 단위면 scale=10)
    byteorder: str  # "little" | "big"
    type: str = "int"  # "int" — signed 정수, "float" — IEEE754 단정도 (usage/package/tdp)


class FrameEncoder:
    def __init__(self, template: bytes, fields: list[FieldSpec]):
        """template: 고정 헤더/테일을 포함한 원형 프레임."""
        self.template = bytearray(template)
        self.fields = fields
        for f in fields:  # 필드가 프레임 밖이면 즉시 설정 오류
            if f.offset + f.size > len(template):
                raise ValueError(f"field {f.name} exceeds frame size {len(template)}")

    def encode(self, metrics: dict) -> bytes:
        frame = bytearray(self.template)
        for f in self.fields:
            value = metrics[f.name]
            if value is None:
                continue  # 센서 부재 시 템플릿 원형 유지
            if f.type == "float":
                fmt = ("<f" if f.byteorder == "little" else ">f")
                frame[f.offset:f.offset + 4] = struct.pack(fmt, value * f.scale)
            else:  # signed — 음수 온도(-°C)도 2의 보수로 그대로 실림
                frame[f.offset:f.offset + f.size] = \
                    int(value * f.scale).to_bytes(f.size, f.byteorder, signed=True)
        return bytes(frame)


def build_frame(payload: bytes) -> bytes:
    """payload 앞에 CRC32(LE)를 붙여 253B 프레임 반환 — CRC가 뒤면 MCU 무응답."""
    if len(payload) != PAYLOAD_SIZE:
        raise ValueError(f"payload must be {PAYLOAD_SIZE} bytes, got {len(payload)}")
    return struct.pack("<I", zlib.crc32(payload) & 0xFFFFFFFF) + payload


def load_layout(path: Path) -> FrameEncoder:
    data = json.loads(path.read_text())
    return FrameEncoder(
        bytes.fromhex(data["template_hex"]),
        [FieldSpec(**f) for f in data["fields"]],
    )
