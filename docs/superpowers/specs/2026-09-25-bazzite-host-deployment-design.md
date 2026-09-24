# AM-02 Bazzite 호스트 배포 설계

> 상태: 사용자 문서 검토 대기 (2026-09-25)

## 목표와 범위

AYANEO AM-02 본체를 NixOS에서 Bazzite로 바꾼 뒤에도 기존 Python 데몬이 부팅 후 전면 서브스크린에 시각과 CPU/GPU 온도를 전송한다. 내부 F1C200s 보드의 앱·펌웨어 변경은 별도 단계에서 다룬다.

- 기존 `src/am02_subscreen/`의 센서 수집, `layout.json` 기반 인코딩, `/dev/ttyS0` 전송 동작을 유지한다.
- `flake.nix`와 `nix/module.nix`는 현재 브랜치에 유지한다. NixOS 작업은 `nixos-archive-2026-09-25` tag에도 보존되어 있다.
- Bazzite의 read-only 시스템 이미지에 Python 패키지를 layer하지 않는다. 사용자 홈의 `uv` venv와 native systemd user service를 사용한다.

## 실행 구조

```text
~/.local/share/am02-subscreen/ (이 저장소 checkout)
  ├── .venv/bin/am02-subscreend  ← uv sync --frozen --no-dev
  ├── layout.json
  └── bazzite/
      ├── am02-subscreen.service
      └── wait-time-sync.sh

systemd --user → NTP 최대 60초 대기 → Python 데몬
                                  ├── /sys/class/hwmon 읽기
                                  └── /dev/ttyS0, 115200 8N1 송신
```

`am02-subscreen.service`는 `%h/.local/share/am02-subscreen` 아래의 venv 실행 파일과 `layout.json`을 명시적으로 참조한다. 사용자에게 `/dev/ttyS0`의 host 그룹 권한을 부여하고 `loginctl enable-linger`로 로그인 전 시작을 허용한다. 서비스 재시작 정책은 기존 NixOS 서비스와 같이 `Restart=always`, `RestartSec=5`이다.

기존 서브스크린 펌웨어는 `year != 0`인 첫 프레임에서만 RTC를 동기화한다. 서비스 시작 전에 host의 `NTPSynchronized` 상태를 최대 60초 확인하고, 시간 내 동기화되지 않으면 기존 NixOS 서비스처럼 데몬을 시작한다. 이 경우 최초 프레임의 시각이 부정확할 수 있음을 배포 문서에 명시한다.

## 설치와 업데이트

`README.md`에 Bazzite 설치, 장치 그룹 확인, `uv sync --frozen --no-dev`, user service 등록, linger 설정, 로그 확인과 업데이트 절차를 적는다. 서비스 파일은 저장소에서 사용자 systemd 디렉터리로 복사한다. 코드 업데이트 시 저장소를 갱신하고 `uv sync --frozen --no-dev`를 다시 실행한 뒤 서비스를 재시작한다. `uv`는 Bazzite에서 지원하는 Homebrew CLI 설치 경로를 사용한다.

`.ai/RULES.md`와 `ROADMAP.md`의 현재 호스트 OS 설명을 Bazzite로 갱신한다. 과거 NixOS 실험·설계 기록은 역사적 사실로 유지한다.

## 검증 기준

1. `uv run pytest`가 통과하고 기존 protocol golden frame이 동일하다.
2. `bash -n`과 `systemd-analyze --user verify`가 새 스크립트·서비스 파일의 구문을 통과한다.
3. Bazzite 실기에서 cold boot 후 로그인 전 서비스가 시작되고, `/dev/ttyS0` 접근 및 시각·온도 표시가 확인된다. 60초 동안 60±1회 갱신, suspend/resume 후 재개 여부도 확인한다.

실기 접근이 없는 개발 환경에서는 3번을 완료했다고 주장하지 않는다.
