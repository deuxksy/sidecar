# ayaneo-am02-subscreen — Agent Rules

AM02 서브스크린 데몬: hwmon 센서 → layout.json 인코딩 → /dev/ttyS0 전송.

## 명령

- 테스트: `uv run pytest` (하드웨어 불필요, pyserial loop://)
- 패키지: `nix build .#am02-subscreen`
- 실기 probe: `sudo ./scripts/probe.sh demo 10 500`

## 하드웨어 주의

- /dev/ttyS0은 dialout 미소속 → sudo 필수
- MCU RTC는 첫 프레임(year≠0)에만 래치 — 시계 갱신 안 되면 전원 차단 리셋 필요
- 프레임 공급 중단 시 MCU 화면 꺼짐 (재전송 시 복귀)
- `@118 style`≠0 전송 금지 (시계 소실)

## 코딩

- 프로토콜 변경 시 docs/protocol.md + golden 테스트 동시 갱신
- 커밋: Conventional Commits
