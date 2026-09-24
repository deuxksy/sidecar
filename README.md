# AYANEO AM-02 Sidecar

AYANEO AM-02 미니 PC 본체(x86_64 Bazzite)와 전면 보조 컴퓨터(Allwinner F1C200s ARM Linux)를 연결하는 **Sidecar** 프로젝트입니다.

현재 내부 시리얼 링크(`/dev/ttyS0`, 115200 8N1)를 통해 실시간 시스템 정보(시계, CPU/GPU 온도)를 전송하는 경량 Linux 데몬(v0.1.0)이 구현되어 있으며, 향후 서브스크린 독립화 및 커스텀 UI/스트림덱으로 확장될 예정입니다. ([로드맵](ROADMAP.md) 참조)

---

## 🚀 빠른 시작 (Quick Start)

### Bazzite 서비스 설정

본체에서 [Homebrew](https://docs.bazzite.gg/Installing_and_Managing_Software/Homebrew/)로 `uv`를 설치하고 저장소를 서비스가 참조하는 경로에 배치합니다.

```bash
brew install uv
mkdir -p ~/.local/share
git clone https://github.com/deuxksy/sidecar.git ~/.local/share/am02-subscreen
cd ~/.local/share/am02-subscreen
uv sync --frozen --no-dev
stat -c '%G %a' /dev/ttyS0
id -nG
```

`/dev/ttyS0`의 그룹이 `dialout`이고 현재 사용자 그룹 목록에 없다면 [Bazzite의 그룹 추가 안내](https://docs.bazzite.gg/Advanced/add-user-to-group/)를 따라 `dialout`을 등록한 뒤 재부팅합니다. Bazzite에서는 `dialout`이 `/usr/lib/group`에만 있고 `/etc/group`에 없을 수 있어 `usermod`만으로는 등록되지 않습니다. 다른 그룹이면 해당 장치의 실제 소유 그룹과 권한을 먼저 확인합니다.

```bash
cd ~/.local/share/am02-subscreen
sudo loginctl enable-linger "$USER"
mkdir -p ~/.config/systemd/user
cp bazzite/am02-subscreen.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now am02-subscreen.service
```

`linger`는 로그인 전에도 user service를 시작합니다. 서비스 상태와 로그는 다음 명령으로 확인합니다.

```bash
systemctl --user status am02-subscreen.service
journalctl --user -u am02-subscreen.service -f
```

업데이트 후에는 의존성을 lockfile에 맞추고 서비스를 재시작합니다.

```bash
cd ~/.local/share/am02-subscreen
git pull --ff-only
uv sync --frozen --no-dev
cp bazzite/am02-subscreen.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user restart am02-subscreen.service
```

서비스는 NTP 동기화를 최대 약 60초 기다립니다. 그동안 동기화되지 않으면 데몬을 시작하므로 첫 프레임에서만 시각을 받아들이는 순정 펌웨어의 표시 시각이 틀릴 수 있습니다.

### 테스트 및 빌드

```bash
# 테스트 실행 (하드웨어 없이 loop:// 시리얼로 검증)
uv run pytest

# 패키지 빌드
nix build .#am02-subscreen

# 로컬 직접 실행
uv run am02-subscreend /dev/ttyS0 --layout layout.json
```

### NixOS 서비스 설정 (기존 배포)

Flake 입력에 추가하고 서비스를 활성화합니다:

```nix
{
  inputs.am02-subscreen.url = "github:deuxksy/ayaneo-am02-subscreen";

  # NixOS 시스템 구성:
  imports = [ am02-subscreen.nixosModules.default ];

  services.am02-subscreen.enable = true;
  # services.am02-subscreen.port = "/dev/ttyS0";  # 기본값
}
```

---

## 📐 아키텍처 (Architecture)

```text
sensors.py                protocol.py                  transport.py
hwmon sysfs ────collect()───▶ layout.json ────encode()───▶ /dev/ttyS0 (115200 8N1)
(k10temp, amdgpu 온도)        프레임 템플릿 + 필드 오프셋         ▲ 쓰기 실패 시
                              (CRC32 4B 앞단 패킹)             지수 백오프 자동 재연결
```

---

## 📚 문서 허브 (Diátaxis Documentation)

### 1. 튜토리얼 (Tutorials)
- [빠른 시작 가이드](#-빠른-시작-quick-start) - 로컬 테스트 및 개발 환경 구성

### 2. 하우투 가이드 (How-To Guides)
- [Bazzite 서비스 배포](#bazzite-서비스-설정) - native systemd user service 등록 절차
- [NixOS 서비스 배포](#nixos-서비스-설정) - AM02 전용 NixOS 데몬 등록 절차

### 3. 참고자료 (Reference)
- [프로젝트 로드맵](ROADMAP.md) - Sidecar 비전 및 마일스톤 (Shell 개방, SSH, 커스텀 UI)
- [문서 총괄 허브](docs/README.md) - 저장소 전체 문서 디렉터리 구조 안내
- [OKF 사양서 허브](docs/okf/README.md) - AM-02 서브스크린 기술 사양 및 역설계 문서 모음
- [시리얼 프로토콜 명세서](docs/okf/reference/protocol.md) - 253B 와이어 포맷, CRC32 체크섬, MCU RTC 래치 동작

### 4. 설명 및 분석 (Explanation)
- [Phase 0 진단 및 분석](docs/okf/explanation/phase0.md) - 네이티브 UART 하드웨어 분석 및 프로브 역컴파일 과정

---

## 📄 라이선스 (License)

[MIT License](LICENSE)
