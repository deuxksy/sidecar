"""레이아웃 지정대로 바이트가 조립되는지 검증 (프로토콜 미확정 단계이므로 합성 레이아웃 사용)."""
from pathlib import Path

import pytest

from am02_subscreen.protocol import FieldSpec, FrameEncoder, load_layout


def test_encode_writes_fields_at_offsets():
    template = bytes.fromhex("AA01000000FF")  # 헤더 AA01 + 페이로드 5B + 테일 FF
    fields = [
        FieldSpec("cpu_temp", offset=2, size=2, scale=1.0, byteorder="little"),
        FieldSpec("gpu_temp", offset=4, size=1, scale=1.0, byteorder="little"),
    ]
    enc = FrameEncoder(template, fields)

    frame = enc.encode({"cpu_temp": 44.0, "gpu_temp": 42.0})

    assert frame == bytes.fromhex("AA01" + "2C00" + "2A" + "FF")


def test_scale_applies_before_pack():
    enc = FrameEncoder(b"\x00\x00", [FieldSpec("cpu_temp", 0, 2, scale=10.0, byteorder="little")])
    assert enc.encode({"cpu_temp": 4.4}) == (44).to_bytes(2, "little")


def test_encode_keeps_template_when_sensor_none():
    # collect()는 센서 부재 시 None 반환 — 해당 필드는 템플릿 원형 유지
    enc = FrameEncoder(b"\xAA\x00\xFF", [FieldSpec("cpu_temp", 1, 1, scale=1.0, byteorder="little")])
    assert enc.encode({"cpu_temp": None}) == b"\xAA\x00\xFF"


def test_field_exceeding_frame_raises():
    with pytest.raises(ValueError):
        FrameEncoder(b"\x00", [FieldSpec("cpu_temp", 0, 2, scale=1.0, byteorder="little")])


def test_load_layout_builds_encoder(tmp_path):
    layout = tmp_path / "layout.json"
    # brief의 원래 template_hex "AAFF"는 2바이트라 필드(offset 0, size 2)가 프레임 전체를
    # 덮어 tail FF가 남지 않는다 — 3바이트 "AA00FF"로 수정 (단언은 brief 그대로 유지)
    layout.write_text(
        '{"template_hex": "AA00FF",'
        ' "fields": [{"name": "cpu_temp", "offset": 0, "size": 2, "scale": 10.0, "byteorder": "little"}]}'
    )
    enc = load_layout(layout)
    assert enc.encode({"cpu_temp": 2.5}) == bytes([25, 0]) + b"\xFF"
