# AM-02 Subscreen Linux 데몬 설계

> **Status**: Approved (2026-08-25)
> **Target**: AYANEO AM-02 (Ryzen 7 7840HS) + NixOS

## 목차

- [목표](#목표)
- [배경 — 하드웨어 사실관계](#배경--하드웨어-사실관계)
- [아키텍처](#아키텍처)
- [컴포넌트](#컴포넌트)
- [실행 단계](#실행-단계)
- [에러 처리](#에러-처리)
- [검증 기준](#검증-기준)
- [리스크](#리스크)
- [확장 계획 — Debian/Fedora](#확장-계획--debianfedora)

## 목표

AM-02 전면 디스플레이(subscreen)에 Windows AYASPACE와 동일한 수준의 시스템 정보(시계, CPU/GPU 온도, 팬 속도, 부하)를 NixOS에서 표시한다. GPU는 Ryzen 7 7840HS 내장 Radeon 780M(iGPU)로 한정한다.

**성공 기준**: NixOS 부팅 후 subscreen에 시계 + CPU/GPU 온도가 표시되고 주기적으로 갱신된다.

**비목표 (Out of Scope)**:

- 커스텀 이미지/애니메이션/비디오 표시 (커스텀 펌웨어 경로)
- subscreen 펌웨어 수정 또는 재플래시
- AYASPACE의 모든 화면(위젯 갤러리 등) 재현 — 시스템 정보 표시만

## 배경 — 하드웨어 사실관계

커뮤니티 리버스 엔지니어링([r/ayaneo 스레드](https://www.reddit.com/r/ayaneo/comments/1isly3s/the_ayaneo_am02_subscreen_customization/))로 확인된 구조:

| 항목 | 사실 |
| :--- | :--- |
| 제어 칩 | 독립 컨트롤러 보드 — Allwinner F1C200s (ARM9, 32MB DDR SiP) |
| 펌웨어 | 내장 SD 카드에서 Buildroot Linux 부팅, 메인 OS와 완전 독립 |
| UI 스택 | tslib(터치) + framebuffer 렌더링 |
| GUI 데몬 | `/data/app/minipc-screen-launcher/bin/minipc-screen-launcher` |
| 호스트 통신 데몬 | `/data/app/launcher-comm` — 시리얼(COM) 115200 baud |
| 데몬 간 IPC | shared_memory |
| Windows | AYASPACE가 시리얼로 시스템 정보를 전송 |
| Linux | 해당 역할을 하는 소프트웨어 없음 → 본 프로젝트가 채움 |

즉 장치가 표준 **CDC-ACM으로 인식되는 한 커널 드라이버는 불필요**하다. subscreen은 이미 독립 실행 중이며, 호스트 쪽에서 시리얼 프로토콜로 데이터를 보내주는 사용자 공간 데몬만 있으면 된다. (CDC-ACM 미인식 시에만 `usbserial` vendor 파라미터로 대응 — 리스크 표 참조)

## 아키텍처

```text
[수집] 표준 sysfs/proc만 사용 (/sys/class/hwmon, /proc/stat, RTC)
   ↓  — 배포판 무관 (NixOS/Debian/Fedora 동일 경로)
[코어] am02-subscreend — 사용자 공간 데몬 (Python 3 + pyserial 단일 의존)
   ↓
[전송] udev by-id 심링크로 고정된 /dev/ttyACM* (115200 baud)
   ↓
[표시] 기존 subscreen 펌웨어(launcher-comm)가 시계/온도 렌더링
```

핵심 원칙: **코어와 패키징의 분리**. 코어 데몬은 배포판 독립적으로 유지하고, 배포판별 코드는 얇은 패키징 레이어에만 존재한다.

## 컴포넌트

1. **`docs/protocol.md`** — 역설계 산출물. 캡처된 AYASPACE↔subscreen 프로토콜 문서. 필수 산출 항목: 프레임 경계(framing), 메시지 타입, 필드↔값 매핑, byte order, 체크섬 알고리즘, handshake/ACK 존재 여부, 전송 주기
2. **`am02-subscrend`** — 메인 데몬. 수집 → 인코딩 → 전송 루프 (1초 주기). 설정은 표시 항목 ON/OFF 정도로 최소화
   - 센서 탐색: hwmon `name`/`label` 기반 (`k10temp`→`Tctl`, `amdgpu`→`edge`), 부팅 시마다 재탐색 (hwmon 번호는 부팅마다 변동)
3. **프로토콜 인코더 모듈** — 프레임 직렬화만 담당. 코어 루프에서 분리하여 단위 테스트 대상으로 격리
4. **`nix/module.nix`** — NixOS 서비스 정의 (`systemd.services`) + udev 규칙
   - 시리얼 고정: VID/PID 매칭으로 커스텀 심링크 `/dev/am02-subscreen` 생성 (장치에 시리얼번호가 없을 수 있어 `/dev/serial/by-id` 의존하지 않음)
   - 서비스 ordering: `/dev/am02-subscreen` device unit 의존 (`After=`/`Requires=`) — 심링크 생성 전 시작 방지

## 실행 단계

- **Phase 0 — 진단** (NixOS에서 즉시): `lsusb`, `dmesg | grep -iE 'tty|cdc'`, `/dev/ttyACM*` 확인 → subscreen의 USB VID/PID와 장치 노드 확보
- **Phase 1 — 캡처 역설계** (Windows 1회 부팅): USBPcap + Wireshark으로 AYASPACE 구동 중 시리얼 트래픽 캡처 → 프레임 구조 분석 → `protocol.md` 작성
  - 분석 순서: 프레임 경계 식별 → 메시지 타입 분류 → 온도 인위 변경(스트레스 툴)으로 필드 오프셋 확정 → byte order/체크섬 검증 → handshake/ACK 존재 확인
- **Phase 2 — 데몬 구현**: 프로토콜 인코더 TDD (캡처 프레임 재생성 일치) → 수집기 연결 → 실기 연동
- **Phase 3 — NixOS 패키징**: flake + NixOS module + udev 규칙, 부팅 시 자동 시작

## 에러 처리

필요한 것만 (불가능한 시나리오 과대처리 금지). 프로토콜에 ACK/read-back 경로가 있다는 것이 Phase 1에서 확인되기 전까지, 호스트는 화면 상태를 관측할 수 없다는 전제로 작성한다:

- 시리얼 장치 부재/지연(부팅 초기) → 지수 백오프 재시도 (subscreen이 메인 OS보다 늦게 준비되는 케이스)
- **serial write 실패 감지 시** (장치 사라짐, suspend/resume 후 재인식, 부분 write) → 로그 1줄 + 장치 재오픈 루프로 재개. 화면 렌더링 성공 여부는 관측하지 않는다

## 검증 기준

| 단계 | Verify |
| :--- | :--- |
| Phase 0 | 장치 노드와 VID/PID가 문서화됨. cold boot 3회 + USB 재연결 3회 모두에서 동일 심링크(`/dev/am02-subscreen`) 생성됨 |
| Phase 1 | 스트레스 툴로 온도 인위 변경 시 캡처 프레임 내 대응 바이트 오프셋 변화가 확인됨. 동일 조건 재캡처 시 프레임 바이트 시퀀스가 재현됨 |
| Phase 2 | 인코더 단위 테스트: 캡처된 실제 프레임(golden frame)을 코드로 재생성 → 바이트 단위 일치. PTY mock 시리얼로 1초 주기 전송 루프 단위 테스트 |
| Phase 3 | 실기: 부팅 후 subscreen에 시계+온도 표시. 60초 관측 시 60±1회 갱신, 표시 온도 = hwmon 센서값 ±1°C. cold boot 3회 연속 자동 시작. `systemctl suspend` 1회 후 갱신 재개 (최종 성공 기준) |

## 리스크

| 리스크 | 확률 | 대응 |
| :--- | :--- | :--- |
| 프로토콜이 바이너리+체크섬으로 단순 캡처만으로 해석 어려움 | 중 | 반복 패턴/필드 정렬 분석, 온도 값을 인위적으로 변경하며 diff 캡처 |
| 프로토콜이 obfuscation/암호화됨 | 저 | 백업 경로: 기기 분해 후 F1C200s UART 콘솔 진입 → `launcher-comm` Ghidra 분석 |
| Linux에서 장치가 CDC-ACM으로 열리지 않음 (vendor-specific USB) | 저 | Phase 0에서 즉시 판명. 필요시 usbserial vendor 파라미터로 대응 |

## 확장 계획 — Debian/Fedora

코어가 배포판 독립적이므로 확장은 패키징 추가만으로 가능하다 (YAGNI: 초기 구현 제외, 요청 시 진행):

| 레이어 | NixOS (1차) | Debian/Fedora (2차) |
| :--- | :--- | :--- |
| 코어 데몬 | 동일 | 동일 |
| 서비스 | NixOS module | 동일 systemd unit + `.deb`/`.rpm` |
| 시리얼 고정 | udev rule | 동일 udev rule |

## 참고 자료

- [r/ayaneo — AM02 subscreen customization 스레드](https://www.reddit.com/r/ayaneo/comments/1isly3s/the_ayaneo_am02_subscreen_customization/) — 하드웨어 구조/데몬 경로/통신 방식의 1차 출처
- [ShadowBlip/ayaneo-platform](https://github.com/ShadowBlip/ayaneo-platform) — AYANEO Linux 드라이버 (subscreen 미지원 확인)
- [aodzip/buildroot-tiny200](https://github.com/aodzip/buildroot-tiny200) — F1C100s/200s Buildroot 툴체인 (백업 경로용)
- [Liliputing AM02 리뷰](https://liliputing.com/ayaneo-retro-mini-pc-am02-review/) — Linux에서 subscreen 데이터 미표시 확인
