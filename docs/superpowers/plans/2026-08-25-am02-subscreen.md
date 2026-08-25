# AM-02 Subscreen Linux 데몬 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** AYANEO AM-02 전면 subscreen에 NixOS에서 수집한 시계/CPU/GPU 온도를 시리얼(ttyS0)로 전송해 표시하는 사용자 공간 데몬.

**Architecture:** 수집(hwmon sysfs) → 인코딩(레이아웃 기반 프레임 인코더) → 전송(재연결 내장 시리얼 transport) 3계층. 프로토콜 역설계 결과는 코드가 아닌 `layout.json`(데이터)으로 주입해, 캡처 결과가 나와도 코드 변경이 없도록 분리. 배포는 NixOS systemd 서비스.

**Tech Stack:** Python 3.11+, pyserial(유일 런타임 의존성), pytest, Nix flake + NixOS module.

## Global Constraints

- 시리얼 포트: `/dev/ttyS0` (네이티브 16550A, 0x3f8, IRQ 3), 115200 8N1 — Phase 0 확정
- 수집 주기: 1초
- 런타임 의존성: pyserial만 (표준라이브러리 외)
- fan 속도 표시 제외 — hwmon에 fan 노드 없음 (Phase 0 확정)
- 데몬 실행 계정: dialout 그룹 시스템 유저 (root 아님)
- 테스트는 하드웨어 없이 실행 가능해야 함 (PTY/loop:// 가상 시리얼)
- 커밋: Conventional Commits (말머리 영어, 본문 한국어)

---

### Task 1: 진단 문서화 + 스펙 갱신 + 프로브 스크립트

**Files:**
- Create: `docs/phase0.md`
- Create: `scripts/probe.sh`
- Modify: `docs/superpowers/specs/2026-08-25-am02-subscreen-design.md`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces: `docs/phase0.md` — Task 5(캡처 게이트)의 판단 근거. 스펙의 udev/VID:PID 섹션을 네이티브 UART 사실로 교체

- [ ] **Step 1: `docs/phase0.md` 작성**

```markdown
# Phase 0 진단 결과 (2026-08-25, AM02 본체 NixOS에서 측정)

| 항목 | 값 |
| :--- | :--- |
| DMI | AYANEO Retro Mini PC AM02 |
| subscreen USB 장치 | **없음** (USB 트리에 Intel BT 8087:0032 + xHCI 허브만 존재) |
| 시리얼 포트 | `/dev/ttyS0` — 16550A, I/O 0x3f8, IRQ 3, base_baud 115200, ACPI PNP(00:00) 선언 |
| 결론 | Windows "COM port" = USB가 아닌 보드 내장 UART. subscreen 링크 후보 1순위 |
| CPU 온도 | `/sys/class/hwmon/hwmon*/` name=k10temp, temp1_label=Tctl, 값 milli-°C |
| GPU 온도 | name=amdgpu, temp1_label=edge, 값 milli-°C |
| fan | hwmon에 fan 노드 없음 → v1 제외 |
| 권한 | /dev/ttyS0 root:dialout 660, 일반 유저 접근 불가 → dialout 그룹으로 해결 |
```

- [ ] **Step 2: 프로브 스크립트 작성** — `scripts/probe.sh`

```bash
#!/usr/bin/env bash
# ttyS0 프로브: 패시브 리슨(송신 없음) 후 간단 ASCII 프로브.
# 사용: sudo ./scripts/probe.sh [listen|probe]
set -euo pipefail
PORT=/dev/ttyS0
stty -F "$PORT" 115200 raw -echo -echoe -echok
case "${1:-listen}" in
  listen)
    echo "[*] 5초 패시브 리슨 ($PORT 115200) — subscreen이 먼저 뭔가 보내오는지 확인"
    timeout 5 dd if="$PORT" bs=1 count=256 2>/dev/null | xxd || true
    echo "[*] 종료 (출력 없으면 수신 없음)" ;;
  probe)
    echo "[*] ASCII 프로브 전송 후 5초 응답 대기"
    printf 'T=45\n' > "$PORT"
    timeout 5 dd if="$PORT" bs=1 count=256 2>/dev/null | xxd || true ;;
esac
```

- [ ] **Step 3: 스펙 갱신** — USB 가정을 네이티브 UART 사실으로 교체 (surgical)
  - `아키텍처` 다이어그램의 `udev by-id 심링크로 고정된 /dev/ttyACM*` → `네이티브 UART /dev/ttyS0 (ACPI PNP, 항상 고정)`
  - `컴포넌트` 4번: udev VID/PID 심링크/`After=` device unit 문단 → 다음으로 교체:

```markdown
   - 접근 권한: 시스템 유저를 dialout 그룹에 추가 (/dev/ttyS0은 root:dialout 660)
   - 서비스 ordering: `After=dev-ttyS0.device` — 장치 노드 준비 후 시작
```

  - 검증 기준 Phase 0 행 → `장치가 /dev/ttyS0(16550A, ACPI PNP)로 확인됨. 프로브 스크립트 결과가 docs/phase0.md에 기록됨`
  - `배경` 표의 호스트 통신 행 → `launcher-comm — 시리얼 115200 baud (AM02에서 네이티브 UART /dev/ttyS0)`
  - 리스크 표 `CDC-ACM으로 열리지 않음` 행 삭제 (USB 아니므로 무관)

- [ ] **Step 4: 커밋**

```bash
git add docs/phase0.md scripts/probe.sh docs/superpowers/specs/
git commit -m "feat: Phase 0 진단 문서화 및 ttyS0 프로브 스크립트"
```

- [ ] **Step 5: USER GATE — 프로브 실행 (사용자)**

세션에서 `! sudo ./scripts/probe.sh listen` 입력해 실행 (sudo는 사용자만 가능). 결과(수신 바이트 유무)를 `docs/phase0.md`에 추가하고 커밋. **수신 데이터가 있으면 Task 5의 Windows 캡처가 불필요할 수 있음 (리스너 출력을 프로토콜 단서로 사용)**.

---

### Task 2: 온도 수집기 (TDD)

**Files:**
- Create: `src/am02_subscreen/sensors.py`
- Test: `tests/test_sensors.py`

**Interfaces:**
- Consumes: 없음
- Produces: `collect(hwmon_root: Path = Path("/sys/class/hwmon")) -> dict` — `{"cpu_temp": float|None, "gpu_temp": float|None, "unix_ts": float}` (온도는 °C)

- [ ] **Step 1: 실패 테스트 작성**

```python
"""collect()가 hwmon name/label 기반으로 온도를 찾는지 검증 (가짜 sysfs 트리 사용)."""
from pathlib import Path
from am02_subscreen.sensors import collect


def _make_hwmon(root: Path, n: int, name: str, labels: dict[str, int]):
    d = root / f"hwmon{n}"
    d.mkdir(parents=True)
    (d / "name").write_text(name)
    for i, (label, milli) in enumerate(labels.items(), start=1):
        (d / f"temp{i}_label").write_text(label)
        (d / f"temp{i}_input").write_text(str(milli))
    return d


def test_collect_reads_k10temp_tctl_and_amdgpu_edge(tmp_path):
    _make_hwmon(tmp_path, 0, "nvme", {"Composite": 40000})
    _make_hwmon(tmp_path, 1, "k10temp", {"Tctl": 44625, "Tdie": 44000})
    _make_hwmon(tmp_path, 2, "amdgpu", {"edge": 42000, "junction": 43500})

    metrics = collect(tmp_path)

    assert metrics["cpu_temp"] == 44.625
    assert metrics["gpu_temp"] == 42.0
    assert metrics["unix_ts"] > 0


def test_collect_returns_none_when_sensor_missing(tmp_path):
    _make_hwmon(tmp_path, 0, "nvme", {"Composite": 40000})

    metrics = collect(tmp_path)

    assert metrics["cpu_temp"] is None
    assert metrics["gpu_temp"] is None
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd /home/crong/git/ayaneo && python3 -m pytest tests/test_sensors.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'am02_subscreen'`

- [ ] **Step 3: 최소 구현**

```python
"""AM02 시스템 정보 수집 — hwmon name/label 기반 (hwmon 번호는 부팅마다 변동)."""
import time
from pathlib import Path


def read_temperature(hwmon_root: Path, chip: str, label: str) -> float | None:
    """name==chip인 hwmon에서 temp*_label==label인 온도(°C) 반환. 못 찾으면 None."""
    for hwmon in sorted(hwmon_root.glob("hwmon*")):
        if (hwmon / "name").read_text().strip() != chip:
            continue
        for label_file in sorted(hwmon.glob("temp*_label")):
            if label_file.read_text().strip() == label:
                raw = int((hwmon / f"{label_file.stem}_input").read_text())
                return raw / 1000.0
    return None


def collect(hwmon_root: Path = Path("/sys/class/hwmon")) -> dict:
    return {
        "cpu_temp": read_temperature(hwmon_root, "k10temp", "Tctl"),
        "gpu_temp": read_temperature(hwmon_root, "amdgpu", "edge"),
        "unix_ts": time.time(),
    }
```

디렉토리 생성: `src/am02_subscreen/__init__.py` (빈 파일), `tests/__init__.py` (빈 파일), `pyproject.toml`:

```toml
[project]
name = "am02-subscreen"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["pyserial>=3.5"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_sensors.py -v`
Expected: PASS 2건

- [ ] **Step 5: 커밋**

```bash
git add src/ tests/ pyproject.toml
git commit -m "feat: hwmon name/label 기반 온도 수집기"
```

---

### Task 3: 레이아웃 기반 프레임 인코더 (TDD)

**Files:**
- Create: `src/am02_subscreen/protocol.py`
- Create: `layout.json` (초기값 — 캡처 전 임시)
- Test: `tests/test_protocol.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `FieldSpec(name: str, offset: int, size: int, scale: float, byteorder: str)`
  - `FrameEncoder(template: bytes, fields: list[FieldSpec]).encode(metrics: dict) -> bytes`
  - `load_layout(path: Path) -> FrameEncoder` — `layout.json` 읽어 FrameEncoder 생성

- [ ] **Step 1: 실패 테스트 작성**

```python
"""레이아웃 지정대로 바이트가 조립되는지 검증 (프로토콜 미확정 단계이므로 합성 레이아웃 사용)."""
from pathlib import Path
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


def test_load_layout_builds_encoder(tmp_path):
    layout = tmp_path / "layout.json"
    layout.write_text(
        '{"template_hex": "AAFF",'
        ' "fields": [{"name": "cpu_temp", "offset": 0, "size": 2, "scale": 10.0, "byteorder": "little"}]}'
    )
    enc = load_layout(layout)
    assert enc.encode({"cpu_temp": 2.5}) == bytes([25, 0]) + b"\xFF"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python3 -m pytest tests/test_protocol.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'am02_subscreen.protocol'`

- [ ] **Step 3: 최소 구현**

```python
"""프레임 인코더 — 레이아웃 데이터(layout.json)만으로 프로토콜을 표현한다.
캡처로 프로토콜이 확정되면 코드 변경 없이 layout.json만 교체하면 된다."""
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FieldSpec:
    name: str      # collect()가 반환하는 metrics 키
    offset: int    # 프레임 내 바이트 오프셋
    size: int      # 바이트 수
    scale: float   # 값 × scale → 정수화 후 패킹 (온도 0.1°C 단위면 scale=10)
    byteorder: str  # "little" | "big"


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
            frame[f.offset:f.offset + f.size] = int(value * f.scale).to_bytes(f.size, f.byteorder)
        return bytes(frame)


def load_layout(path: Path) -> FrameEncoder:
    data = json.loads(path.read_text())
    return FrameEncoder(
        bytes.fromhex(data["template_hex"]),
        [FieldSpec(**f) for f in data["fields"]],
    )
```

초기 `layout.json` (캡처 전 임시값 — Task 5에서 교체):

```json
{
  "template_hex": "0000000000",
  "fields": [
    {"name": "cpu_temp", "offset": 0, "size": 2, "scale": 10.0, "byteorder": "little"},
    {"name": "gpu_temp", "offset": 2, "size": 2, "scale": 10.0, "byteorder": "little"}
  ]
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_protocol.py -v`
Expected: PASS 3건

- [ ] **Step 5: 커밋**

```bash
git add src/am02_subscreen/protocol.py layout.json tests/test_protocol.py
git commit -m "feat: 레이아웃 기반 프레임 인코더"
```

---

### Task 4: 시리얼 transport — 재연결 루프 (TDD)

**Files:**
- Create: `src/am02_subscreen/transport.py`
- Test: `tests/test_transport.py`

**Interfaces:**
- Consumes: pyserial
- Produces: `SerialTransport(target: str, baud: int = 115200).send(data: bytes) -> bool`, `.close()`. `target`은 장치 경로 또는 pyserial URL(`loop://`)

- [ ] **Step 1: 실패 테스트 작성**

```python
"""loop:// 가상 시리얼로 송신 성공/재연결 검증 — 하드웨어 불필요."""
from am02_subscreen.transport import SerialTransport


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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python3 -m pytest tests/test_transport.py -v`
Expected: FAIL — `ModuleNotFoundError` (또는 ImportError: serial)

- [ ] **Step 3: 최소 구현**

```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_transport.py -v`
Expected: PASS 2건

- [ ] **Step 5: 커밋**

```bash
git add src/am02_subscreen/transport.py tests/test_transport.py
git commit -m "feat: 재연결 내장 시리얼 transport"
```

---

### Task 5: USER GATE — 프로토콜 확정 (캡처 또는 프로브)

**Files:**
- Modify: `docs/protocol.md` (Create)
- Modify: `layout.json` (확정값 교체)
- Create: `tests/golden/` (캡처 프레임 fixtures)

**Interfaces:**
- Consumes: Task 1 프로브 결과, Task 3 `layout.json` 스키마
- Produces: `docs/protocol.md` (프레임 경계/메시지 타입/필드 매핑/byte order/체크섬/ACK 여부/주기), 확정된 `layout.json`, `tests/golden/*.bin`

실행 순서 — 앞 단계에서 확정되면 뒷 단계 생략:

- [ ] **Step 1: 프로브 결과 판정 (Linux)**

Task 1 Gate의 `listen`에서 수신 바이트가 있었던 경우: 60초 캡처로 반복 패턴 확인.

```bash
sudo timeout 60 dd if=/dev/ttyS0 bs=1 | xxd > /tmp/subscreen-rx.txt
```

`probe`(`T=45\n` 송신)에 화면/응답 반응이 있었는지도 `docs/protocol.md`에 기록.

- [ ] **Step 2: Windows 캡처 (프로브로 미확정 시)**

1. Windows 부팅 → AYASPACE 설치/구동 (subscreen에 온도 표시 확인)
2. 네이티브 COM 스니핑 — USBPcap은 무의미(USB 아님). com0com + hub4com MITM 사용:
   - com0com 설치 (CPN0↔CPN1 가상 페어 생성, 기본값 사용)
   - 관리자 cmd: `hub4com --route=1:2,1:3 \\.\COM1 \\.\CPN0 \\.\CPN1` — COM1(실제 포트) 트래픽을 CPN 쌍으로 미러링. (COM 번호는 장치 관리자에서 AYASPACE가 사용하는 포트로 확인)
   - CPN0에 터미널(PuTTY 등, 115200) 접속 → 로그 기록
3. 온도 인위 변경(부하 도구)하며 로그에서 변하는 바이트 오프셋 식별
4. 로그 덤프를 리포로 복사 → `xxd`로 프레임 경계/헤더/체크섬 분석

- [ ] **Step 3: `docs/protocol.md` 작성**

스펙이 정의한 산출 항목 전부 포함: 프레임 경계, 메시지 타입, 필드↔값 매핑, byte order, 체크섬 알고리즘, handshake/ACK 존재 여부, 전송 주기.

- [ ] **Step 4: `layout.json` 확정 + golden fixture 생성**

분석 결과를 반영해 `layout.json` 교체. 대표 프레임 3개 이상을 hex에서 바이너리로 저장:

```bash
mkdir -p tests/golden
echo -n "AA012C00 2AFF" | tr -d ' ' | xxd -r -p > tests/golden/frame-001.bin  # 실제 캡처 hex로 교체
```

- [ ] **Step 5: golden 테스트 추가 — `tests/test_golden.py`**

```python
"""캡처된 실제 프레임(golden)을 인코더가 재생성하는지 검증."""
from pathlib import Path
import pytest
from am02_subscreen.protocol import load_layout

GOLDEN = Path(__file__).parent / "golden"
LAYOUT = Path(__file__).parents[1] / "layout.json"


@pytest.mark.parametrize("frame_file,metrics", [
    # 캡처 분석 후 실제 값으로 채운다: ("frame-001.bin", {"cpu_temp": 44.0, "gpu_temp": 42.0, ...}),
])
def test_golden_frame_reproduction(frame_file, metrics):
    enc = load_layout(LAYOUT)
    assert enc.encode(metrics) == (GOLDEN / frame_file).read_bytes()
```

(이 단계의 매개변수화 목록은 캡처 결과에 의존하므로 분석 후 작성한다. fixture가 없으면 파일만 만들어 두고 `pytest -k golden`이 0건 skip.)

- [ ] **Step 6: 커밋**

```bash
git add docs/protocol.md layout.json tests/golden/ tests/test_golden.py
git commit -m "feat: 프로토콜 역설계 결과 반영 (layout.json + golden fixtures)"
```

---

### Task 6: 데몬 통합 루프

**Files:**
- Create: `src/am02_subscreen/__main__.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `collect()`, `load_layout()`, `SerialTransport`
- Produces: `run(target: str, encoder: FrameEncoder, poll: float = 1.0, stop: threading.Event | None = None) -> int` — 전송 성공 프레임 수 반환. 진입점 `python -m am02_subscreen [PORT] [LAYOUT_JSON]`

- [ ] **Step 1: 실패 테스트 작성**

```python
"""run()이 수집→인코딩→전송 후 stop 신호로 종료하는지 검증 (loop:// + monkeypatch)."""
import threading
from pathlib import Path
from am02_subscreen import main as main_mod
from am02_subscreen.main import run
from am02_subscreen.protocol import load_layout

LAYOUT = Path(__file__).parents[1] / "layout.json"


def test_run_sends_one_frame_then_stops(monkeypatch):
    monkeypatch.setattr(main_mod, "collect", lambda: {
        "cpu_temp": 44.0, "gpu_temp": 42.0, "unix_ts": 0.0})

    stop = threading.Event()
    orig_send = main_mod.SerialTransport.send

    def send_once_then_stop(self, data):  # 1회 송신 즉시 종료 — 결정적 테스트
        result = orig_send(self, data)
        stop.set()
        return result

    monkeypatch.setattr(main_mod.SerialTransport, "send", send_once_then_stop)

    sent = run("loop://", load_layout(LAYOUT), poll=0.01, stop=stop)

    assert sent == 1
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python3 -m pytest tests/test_main.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'am02_subscreen.main'`

- [ ] **Step 3: 최소 구현 — `src/am02_subscreen/main.py`**

```python
"""데몬 진입점 — 수집→인코딩→전송 1초 루프. SIGTERM/SIGINT로 정상 종료."""
import signal
import sys
import threading
import time
from pathlib import Path

from .protocol import FrameEncoder, load_layout
from .sensors import collect
from .transport import SerialTransport

DEFAULT_PORT = "/dev/ttyS0"
DEFAULT_LAYOUT = Path(__file__).resolve().parent.parent / "layout.json"


def run(target: str, encoder: FrameEncoder, poll: float = 1.0,
        stop: threading.Event | None = None) -> int:
    tx = SerialTransport(target)
    own_stop = stop is None
    if own_stop:
        stop = threading.Event()
        signal.signal(signal.SIGTERM, lambda *_: stop.set())
        signal.signal(signal.SIGINT, lambda *_: stop.set())
    sent = 0
    while not stop.is_set():
        if tx.send(encoder.encode(collect())):
            sent += 1
        stop.wait(poll)  # sleep 대신: 시그널 즉시 반응
    tx.close()
    return sent


def main() -> None:
    port = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PORT
    layout = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_LAYOUT
    run(port, load_layout(layout))


if __name__ == "__main__":
    main()
```

`__main__.py` (2줄):

```python
from .main import main
main()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_main.py tests/ -v`
Expected: 전체 PASS

- [ ] **Step 5: 커밋**

```bash
git add src/am02_subscreen/main.py src/am02_subscreen/__main__.py tests/test_main.py
git commit -m "feat: 데몬 통합 루프 (수집-인코딩-전송)"
```

---

### Task 7: NixOS 패키징 + 서비스 + 실기 검증

**Files:**
- Create: `flake.nix`
- Create: `nix/module.nix`

**Interfaces:**
- Consumes: Task 6 진입점, `layout.json`
- Produces: `nix build` 패키지, `services.am02-subscreen` NixOS 옵션 (`enable`, `port`)

- [ ] **Step 1: `flake.nix` 작성**

```nix
{
  description = "AYANEO AM-02 subscreen 데몬";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" ];
      forAll = nixpkgs.lib.genAttrs systems;
    in {
      packages = forAll (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in rec {
          default = am02-subscreen;
          am02-subscreen = pkgs.python311Packages.buildPythonApplication {
            pname = "am02-subscreen";
            version = "0.1.0";
            src = ./.;
            format = "other";
            propagatedBuildInputs = [ pkgs.python311Packages.pyserial ];
            installPhase = ''
              # 패키지 디렉터리는 Python 임포트명(am02_subscreen, 밑줄)과 일치해야 함
              mkdir -p $out/bin $out/lib/am02_subscreen $out/share/am02-subscreen
              cp -r src/am02_subscreen/. $out/lib/am02_subscreen/
              # main.py 기본 레이아웃 경로(__file__ parents[2])는 Nix store 내에서
              # 해석되지 않으므로 data file로 별치 설치 후 ExecStart에서 --layout으로 명시 전달
              cp layout.json $out/share/am02-subscreen/layout.json
              cat > $out/bin/am02-subscreend <<EOF
#!${pkgs.python311}/bin/python3
import sys; sys.path.insert(0, "$out/lib")
from am02_subscreen.main import main
main()
EOF
              chmod +x $out/bin/am02-subscreend
            '';
            meta = {
              description = "AYANEO AM-02 subscreen daemon - CPU/GPU temps over /dev/ttyS0";
              mainProgram = "am02-subscreend";
              license = pkgs.lib.licenses.mit;
              platforms = [ "x86_64-linux" ];
            };
          };
        });
      overlays.default = final: prev: {
        am02-subscreen = self.packages.${final.system}.am02-subscreen;
      };
      nixosModules.default = { pkgs, ... }: {
        # 모듈이 pkgs.am02-subscreen을 참조하므로 overlay를 함께 구성
        nixpkgs.overlays = [ self.overlays.default ];
        imports = [ ./nix/module.nix ];
      };
    };
}
```

- [ ] **Step 2: `nix/module.nix` 작성**

```nix
{ config, lib, pkgs, ... }:
let
  cfg = config.services.am02-subscreen;
in {
  options.services.am02-subscreen = {
    enable = lib.mkEnableOption "AM02 subscreen 시스템 정보 데몬";
    port = lib.mkOption {
      type = lib.types.str;
      default = "/dev/ttyS0";
      description = "subscreen 연결 시리얼 포트";
    };
  };
  config = lib.mkIf cfg.enable {
    users.users.am02-sub = {
      isSystemUser = true;
      group = "dialout";  # /dev/ttyS0 root:dialout 660
      home = "/var/empty";
    };
    systemd.services.am02-subscreen = {
      description = "AM02 subscreen system info daemon";
      after = [ "dev-ttyS0.device" ];
      wantedBy = [ "multi-user.target" ];
      serviceConfig = {
        # --layout 명시 필수: main.py 기본 경로는 Nix store에서 해석 불가
        ExecStart = "${pkgs.am02-subscreen}/bin/am02-subscreend ${cfg.port} --layout ${pkgs.am02-subscreen}/share/am02-subscreen/layout.json";
        User = "am02-sub";
        Restart = "always";
        RestartSec = "5";
      };
    };
  };
}
```

- [ ] **Step 3: 빌드 검증**

Run: `nix build .#am02-subscreen && timeout 2 ./result/bin/am02-subscreend loop://; echo "exit=$?"`
Expected: 빌드 성공, exit=124 (timeout 종료 — 진입점이 loop://로 1초 주기 전송 중임을 증명. `--help`는 미지원: argv[1]을 포트로 해석하므로 절대 전달 금지)

- [ ] **Step 4: 실기 적용 + Acceptance 체크리스트**

호스트 설정에서 모듈 import + `services.am02-subscreen.enable = true;` 후:

```bash
sudo nixos-rebuild switch --flake .  # 또는 기존 설정 리포 방식
```

스펙 검증 기준 실행 (docs/phase3.md에 기록):

1. `systemctl status am02-subscreen` — active
2. 60초 카운터로 갱신 60±1회 확인 (화면 시계 초 단위)
3. 표시 온도 = `sensors` 값 ±1°C
4. 재부팅 3회 연속 자동 시작
5. `systemctl suspend` 1회 후 갱신 재개

- [ ] **Step 5: 커밋 + 태그**

```bash
git add flake.nix nix/
git commit -m "feat: NixOS 패키징 및 systemd 서비스 모듈"
git tag v0.1.0
```

---

## Self-Review 결과

1. **스펙 커버리지**: 수집(hwmon name/label)→Task 2, 인코더→Task 3/5, 재연결 에러처리→Task 4, suspend/resume→Task 4+7 체크리스트, NixOS 패키징→Task 7, 검증 기준 전 항목→Task 7 Step 4. fan은 Phase 0 근거로 제외 (Task 1에서 스펙 갱신). gap 없음
2. **플레이스홀더 스캔**: Task 5 Step 5의 매개변수화 목록만 캡처 의존 — 구조상 불가피한 USER GATE로 명시됨. 그 외 "TBD/적절히" 없음
3. **타입 일관성**: `collect()->dict` 키(`cpu_temp`,`gpu_temp`,`unix_ts`) ↔ `FieldSpec.name` ↔ `layout.json` fields.name 일치. `SerialTransport(target)` ↔ `run(target)` ↔ `loop://` 테스트 일치. `load_layout(Path)->FrameEncoder` Task 3 정의 ↔ Task 6 사용 일치
