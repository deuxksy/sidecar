# AYANEO AM-02 Subscreen 데몬

AYANEO AM-02 미니 PC의 전면 서브스크린(시계, CPU/GPU 온도)에 내부 시리얼 링크(/dev/ttyS0, 115200 8N1)를 통해 실시간 시스템 정보를 전송하는 경량 Linux 데몬입니다. Windows 전용 AYASPACE 소프트웨어를 완벽히 대체하며, NixOS systemd 서비스 또는 Python 3 환경에서 독립 실행됩니다.

---

## 🚀 빠른 시작 (Quick Start)

### 테스트 및 빌드

```bash
# 테스트 실행 (하드웨어 없이 loop:// 시리얼로 검증)
uv run pytest

# 패키지 빌드
nix build .#am02-subscreen

# 로컬 직접 실행
python3 -m am02_subscreen /dev/ttyS0 --layout layout.json
```

### NixOS 서비스 설정

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
- [NixOS 서비스 배포](#nixos-서비스-설정) - AM02 전용 NixOS 데몬 등록 절차

### 3. 참고자료 (Reference)
- [문서 총괄 허브](docs/README.md) - 저장소 전체 문서 디렉터리 구조 안내
- [OKF 사양서 허브](docs/okf/README.md) - AM-02 서브스크린 기술 사양 및 역설계 문서 모음
- [시리얼 프로토콜 명세서](docs/okf/reference/protocol.md) - 253B 와이어 포맷, CRC32 체크섬, MCU RTC 래치 동작

### 4. 설명 및 분석 (Explanation)
- [Phase 0 진단 및 분석](docs/okf/explanation/phase0.md) - 네이티브 UART 하드웨어 분석 및 프로브 역컴파일 과정

---

## 📄 라이선스 (License)

[MIT License](LICENSE)
