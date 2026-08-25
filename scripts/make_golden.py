#!/usr/bin/env python3
"""golden 프레임 재생성 — layout.json 또는 FIXED_METRICS 변경 시 실행."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]

from am02_subscreen.protocol import build_frame, load_layout
from test_golden import FIXED_METRICS

out = ROOT / "tests" / "golden" / "state.bin"
out.parent.mkdir(exist_ok=True)
frame = build_frame(load_layout(ROOT / "layout.json").encode(FIXED_METRICS))
out.write_bytes(frame)
print(f"golden 재생성: {out} ({len(frame)}B)")
