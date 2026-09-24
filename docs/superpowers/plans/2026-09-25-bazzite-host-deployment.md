# AM-02 Bazzite Host Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 Python 데몬을 Bazzite에서 로그인 전 자동 시작하고 시각·CPU/GPU 온도를 `/dev/ttyS0`로 전송한다.

**Architecture:** 사용자 홈의 저장소 checkout에 `uv` venv를 만들고 native systemd user service로 실행한다. 서비스 시작 전에 host NTP 상태를 확인하며, 기존 Python protocol과 NixOS 설정은 유지한다.

**Tech Stack:** Python 3.11+, `uv`, Bash, systemd user manager, Bazzite/Homebrew

**Spec:** `docs/superpowers/specs/2026-09-25-bazzite-host-deployment-design.md`

## Global Constraints

- `src/am02_subscreen/`, `layout.json`, `flake.nix`, `nix/module.nix`의 동작을 변경하지 않는다.
- 설치 위치는 `%h/.local/share/am02-subscreen`이며, 의존성 설치 명령은 `uv sync --frozen --no-dev`이다.
- UART는 `/dev/ttyS0`, 115200 8N1이다. 첫 프레임 시각 래치를 위해 NTP 동기화를 최대 약 60초 기다린다.
- 서비스는 `Restart=always`, `RestartSec=5`를 사용하고 `loginctl enable-linger`로 로그인 전 시작한다.
- NixOS 실험 기록은 역사적 사실로 남기고 현재 호스트 OS 설명만 Bazzite로 고친다.

## Review Focus

1. `timedatectl`이 첫 시도에 `yes`를 반환하면 대기 없이 실행한다. Task 1의 즉시 동기화 테스트로 확인한다.
2. NTP 동기화가 늦으면 `yes`가 나올 때까지 재시도한다. Task 1의 지연 동기화 테스트로 확인한다.
3. NTP가 계속 `no`이거나 `timedatectl`이 실패해도 약 60초 뒤 데몬 시작을 허용한다. Task 1의 timeout·명령 실패 테스트로 확인한다.
4. `/dev/ttyS0`가 서비스 시작 시 없으면 기존 `SerialTransport` 재연결 루프가 동작해야 한다. Task 2에서 기존 `tests/test_transport.py`를 실행해 확인한다.
5. `layout.json`은 저장소 checkout에서 명시적으로 읽어야 한다. Task 2의 unit 정적 검사와 `tests/test_main.py` 실행으로 확인한다.

---

## File Map

- `bazzite/wait-time-sync.sh`: 서비스 시작 전 host NTP 상태를 확인하는 작은 Bash 스크립트.
- `tests/test_bazzite_time_sync.py`: `timedatectl`과 `sleep`을 대체해 대기 동작을 검증한다.
- `bazzite/am02-subscreen.service`: venv 실행 파일, layout 경로, 재시작 정책을 선언한다.
- `README.md`: Bazzite 설치·업데이트·진단을 우선 안내하고 NixOS 설정 링크를 유지한다.
- `.ai/RULES.md`, `ROADMAP.md`: 현재 호스트 OS 표기만 갱신한다.

### Task 1: NTP 대기 스크립트

**Files:**
- Create: `tests/test_bazzite_time_sync.py`
- Create: `bazzite/wait-time-sync.sh`

**Interfaces:**
- Consumes: `timedatectl show --property=NTPSynchronized --value`의 `yes`/`no` 출력.
- Produces: 종료 코드 0. `yes`면 즉시 종료하고, 그렇지 않으면 1초 간격으로 최대 60회 확인한다.

- [ ] **Step 1: 동작 테스트 작성**

```python
import os
import subprocess
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "bazzite/wait-time-sync.sh"


@pytest.mark.parametrize(
    ("mode", "expected_calls"),
    [("immediate", 1), ("delayed", 2), ("never", 60), ("error", 60)],
)
def test_wait_time_sync(tmp_path, mode, expected_calls):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    counter = tmp_path / "calls"
    timedatectl = bin_dir / "timedatectl"
    timedatectl.write_text(
        '#!/bin/sh\n'
        'n=$(cat "$TEST_COUNTER" 2>/dev/null || printf 0)\n'
        'n=$((n + 1))\n'
        'printf "%s" "$n" > "$TEST_COUNTER"\n'
        'if [ "$TEST_MODE" = error ]; then exit 1; fi\n'
        'if [ "$TEST_MODE" = immediate ] || '
        '{ [ "$TEST_MODE" = delayed ] && [ "$n" -ge 2 ]; }; then\n'
        '  printf "yes\\n"\n'
        'else\n'
        '  printf "no\\n"\n'
        'fi\n'
    )
    timedatectl.chmod(0o755)
    sleep = bin_dir / "sleep"
    sleep.write_text("#!/bin/sh\nexit 0\n")
    sleep.chmod(0o755)
    env = os.environ | {
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "TEST_COUNTER": str(counter),
        "TEST_MODE": mode,
    }
    result = subprocess.run(["bash", str(SCRIPT)], env=env, timeout=10)
    assert result.returncode == 0
    assert int(counter.read_text()) == expected_calls
```

- [ ] **Step 2: 실패 확인** — `uv run pytest tests/test_bazzite_time_sync.py -q` 실행. 스크립트가 없어서 FAIL이어야 한다.
- [ ] **Step 3: 최소 구현 작성**

```bash
#!/usr/bin/env bash

for ((attempt=0; attempt<60; attempt++)); do
    if [[ "$(timedatectl show --property=NTPSynchronized --value 2>/dev/null)" == yes ]]; then
        exit 0
    fi
    sleep 1
done
```

- [ ] **Step 4: 검증** — `uv run pytest tests/test_bazzite_time_sync.py -q`와 `bash -n bazzite/wait-time-sync.sh`가 모두 PASS여야 한다.
- [ ] **Step 5: commit** — `git add bazzite/wait-time-sync.sh tests/test_bazzite_time_sync.py` 후 `git commit -m 'feat(bazzite): NTP 동기화 대기 추가'`.

### Task 2: systemd user service와 배포 문서

**Files:**
- Create: `bazzite/am02-subscreen.service`
- Modify: `README.md`
- Modify: `.ai/RULES.md`
- Modify: `ROADMAP.md`

**Interfaces:**
- Consumes: Task 1의 `bazzite/wait-time-sync.sh`, `uv sync --frozen --no-dev`가 만든 `.venv/bin/am02-subscreend`, 저장소의 `layout.json`.
- Produces: `am02-subscreen.service` user unit과 Bazzite 설치·업데이트 절차.

- [ ] **Step 1: unit 작성** — `bazzite/am02-subscreen.service`에 다음 내용을 사용한다. user manager는 system `.device` unit에 의존하지 않으며, 장치 부재는 기존 Python transport가 재시도한다.

```ini
[Unit]
Description=AM02 subscreen system info daemon

[Service]
Type=simple
ExecStartPre=/usr/bin/bash %h/.local/share/am02-subscreen/bazzite/wait-time-sync.sh
ExecStart=%h/.local/share/am02-subscreen/.venv/bin/am02-subscreend /dev/ttyS0 --layout %h/.local/share/am02-subscreen/layout.json
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

- [ ] **Step 2: Bazzite 설치 문서 작성** — `README.md`의 첫 문단에서 현재 호스트를 Bazzite로 바꾸고 빠른 시작 앞에 Bazzite 섹션을 추가한다. 아래 명령과 순서를 그대로 설명한다. `/dev/ttyS0`의 그룹이 `dialout`일 때만 `usermod`를 실행하고, 변경 후 재로그인 또는 재부팅해 user manager에 새 그룹이 반영된 다음 서비스를 시작한다.

```bash
brew install uv
git clone https://github.com/deuxksy/sidecar.git ~/.local/share/am02-subscreen
cd ~/.local/share/am02-subscreen
uv sync --frozen --no-dev
stat -c '%G %a' /dev/ttyS0
id -nG
sudo usermod -aG dialout "$USER"  # dialout이 장치 그룹이고 현재 사용자에게 없을 때만
sudo loginctl enable-linger "$USER"
```

새 그룹을 추가했다면 재로그인 또는 재부팅한 뒤 다음 명령을 실행한다.

```bash
cd ~/.local/share/am02-subscreen
mkdir -p ~/.config/systemd/user
cp bazzite/am02-subscreen.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now am02-subscreen.service
```

`systemctl --user status am02-subscreen.service`와 `journalctl --user -u am02-subscreen.service -f`를 진단 명령으로 적는다. 업데이트는 `git pull --ff-only`, `uv sync --frozen --no-dev`, `systemctl --user restart am02-subscreen.service` 순서로 적는다. NTP가 60회 안에 동기화되지 않으면 최초 표시 시각이 틀릴 수 있다는 제한을 명시한다. 기존 NixOS 서비스 절은 과거 사용자용으로 유지한다.

- [ ] **Step 3: 현재 OS 표기 갱신** — `.ai/RULES.md`의 Architecture에 Bazzite user service를 추가한다. `ROADMAP.md`의 비전·호스트 다이어그램·기술 스택·진행 현황에서 현재 호스트를 Bazzite로 바꾸되, Phase 0의 NixOS 완료 기록과 과거 실험 문서는 수정하지 않는다.
- [ ] **Step 4: 정적·회귀 검증** — `systemd-analyze --user verify bazzite/am02-subscreen.service`, `uv run pytest tests/test_transport.py tests/test_main.py tests/test_golden.py -q`, `git diff --check`를 실행한다. user bus 문제로 `systemd-analyze --user`가 불가능하면 `systemd-analyze verify bazzite/am02-subscreen.service`의 결과와 한계를 기록한다.
- [ ] **Step 5: commit** — 변경 파일의 비밀정보·취약 설정을 검토하고 `git add bazzite/am02-subscreen.service README.md .ai/RULES.md ROADMAP.md` 후 `git commit -m 'feat(bazzite): native user service 배포 추가'`.

### Task 3: 전체 검증과 실기 인계

**Files:**
- No source changes expected.

**Interfaces:**
- Consumes: Task 1·2의 스크립트, service, 문서.
- Produces: 로컬 검증 결과와 Bazzite 실기 확인 항목.

- [ ] **Step 1: 전체 테스트** — `uv run pytest`를 실행하고 golden frame과 기존 Python 데몬 회귀가 없음을 확인한다.
- [ ] **Step 2: 구성 검사** — `bash -n bazzite/wait-time-sync.sh`, `systemd-analyze --user verify bazzite/am02-subscreen.service`, `git diff --check`, `git status --short`를 확인한다.
- [ ] **Step 3: 실기 검증 범위 보고** — Bazzite AM-02 접근이 가능하면 cold boot 후 로그인 전 서비스 기동, 시각·온도, 60초 갱신 횟수, suspend/resume을 확인한다. 접근이 없으면 이 항목을 미검증으로 명시하고 적용 명령과 로그 확인 방법을 결과에 포함한다.
