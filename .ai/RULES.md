# AYANEO AM-02 Subscreen Project Rules

## Overview & Architecture
AYANEO AM-02 전면 서브스크린(Allwinner F1C200s 임베디드 리눅스)에 호스트 시스템 정보(CPU/GPU 온도, 시각)를 시리얼로 전송하는 사용자 공간 데몬.

- **Sensors** (`src/am02_subscreen/sensors.py`): `/sys/class/hwmon`에서 k10temp(Tctl), amdgpu(edge) 온도 및 로컬 시각(KST) 수집.
- **Protocol** (`src/am02_subscreen/protocol.py`, `layout.json`): `layout.json` 스키마 기반 필드 인코딩. 프레임 앞에 4B CRC32(LE)를 붙여 총 253바이트(249B payload + 4B CRC) 전송.
- **Transport** (`src/am02_subscreen/transport.py`): `/dev/ttyS0` (115200 baud, 8N1) 시리얼 통신, 에러 시 지수 백오프 재연결.
- **Nix Module** (`nix/module.nix`, `flake.nix`): NixOS systemd 서비스 `services.am02-subscreen`.

## Commands & Workflows
- **Test**: `uv run pytest` 또는 `python3 -m pytest`
- **Build**: `nix build .#am02-subscreen`
- **Run Local**: `python3 -m am02_subscreen /dev/ttyS0 --layout layout.json`

## Critical Gotchas
- **UART Port**: USB CDC-ACM이 아닌 보드 내장 16550A UART (`/dev/ttyS0`). `dialout` 그룹 권한 필수.
- **CRC Placement**: CRC32는 반드시 249바이트 페이로드 **앞(prepend)**에 위치해야 함 (뒤에 붙이면 MCU 무응답).
- **MCU RTC Latch**: 서브스크린 펌웨어는 `year!=0`인 첫 프레임 수신 시 1회만 RTC를 동기화(`flag_5081`)하고 이후 프레임의 시간 필드는 무시함.
