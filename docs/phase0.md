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

## Phase 0 추가 — 프로브 실험 (Task 5, scripts/probe.sh)

2026-08-25 측정. 모든 실험은 `stty raw -echo` 후 수행.

### 관측 요약

| 실험 | 결과 |
| :--- | :--- |
| 패시브 리슨 60s (TX 없음) | **0바이트** — MCU 자발 송신 없음, 호스트 구동 링크 |
| TX `T=45\n` → 5s 수신 ×3 | **`0x00`×29바이트** 결정론적 응답 (od 오프셋 `00001d`) |
| TX ASCII garbage (`\xff`, `\x00` 리터럴) | 동일 `0x00`×29 |
| TX `0xff` 단일 바이트 (실제 binary) | 동일 `0x00`×29 |
| TX `0x00`×29 (관측 프레임 미러) | 동일 `0x00`×29 |
| 수신 baud 57600 | `0x08`×15 — 29에 정비례 |
| 수신 baud 38400 | `20 40 80 00` 회전 ×11 — 29에 정비례 |
| 화면 반응 | 없음 (ASCII/binary 모두 — 렌더링 유지) |
| stty 230400 | EINVAL (이 UART/드라이버 미지원) |

### 해석

1. **break pulse 아님, 실제 프레임**: 순수 break라면 반속 샘플링에서도 전부 `0x00`이어야 하나 57600에서 `0x08`×15 관측. `0x08` = 115200 `0x00` 바이트들(유효 start/stop bit 포함)을 반속으로 샘플링할 때 MCU stop bit(HIGH)가 수신 data bit3에 찍히는 패턴과 정확히 일치. 38400의 `20 40 80 00` 회전 패턴도 1/3 속도 모델과 일치.
2. **응답은 payload 무감각**: 7회 실험 전부 `0x00`×29 — 유효 프레임이 아니면 "빈 상태" 응답 프레임을 돌려주는 것으로 추정. all-zero는 XOR/sum 계열 checksum에서도 통과.
3. **링크 방향성**: MCU는 호스트 TX에만 반응. 트리거 1회 후 60s 수신 = **29바이트뿐, 주기 버스트 없음** → 순수 request-response. 주기 갱신은 호스트가 프레임을 반복 송신하는 구조.

### 커뮤니티 자료 (r/ayaneo 스레드)

- MCU측 `launcher-comm`(시리얼 파서) ↔ `minipc-screen-launcher`(GUI)가 shared memory로 통신 — Ghidra 역컴파일로 **shareData 스키마 공개됨** (온도 32-bit int, usage/power float, RAM/SSD int, 시간은 부팅 후 1회)
- wire format(프레임 구조)은 미공개 — 공개 repo 없음
- 본체 NVMe에 Windows 파티션 없음(전체 NixOS) → Windows MITM 캡처는 재설치 필요. Linux 블랙박스 실험으로 프로토콜 확정 중

## Phase 0 추가 — AYASPACE 3.1 바이너리 정적 분석 (Task 5)

송신 측(Windows AYASPACE) 코드를 직접 읽어 wire format 확보 경로. MITM 캡처 대체.

| 항목 | 값 |
| :--- | :--- |
| 확보 경로 | 공식 API `GET /download/download/item-list?type_id=1` → `AYASpaceGlobalSetup3.1.0.0.exe.zip` (235MB, Tencent COS CDN) |
| 설치 구조 | NSIS → 내부 `app.7z` → CEF 앱 (AYASpace.exe + AYASpaceCef.exe + libcef.dll) |
| 핵심 모듈 | **`AYASpaceCef.exe`** 내 native C++ `CMiniPCLauncher` (`utils_aya\MiniPC_Launcher\CMiniPCLauncher.cpp`, MSVC RTTI 문자열로 확인) |

### CMiniPCLauncher 문자열 증거 (프로토콜 골격)

- `Hardware\DeviceMap\SerialComm` registry 열거로 COM 포트 탐색
- `kOpenSerialPort success` / `OpenSerialPort failed!`
- **CRC32 request-response**: `resPack.recv_crc32 != pack.crc32`, `recv_crc32 %08X pack_crc32: %08X`, `read failed %d/%d`, `retry conut: %d`, `Wait for read over` — MCU 응답 프레임(`resPack`)에 수신 CRC를 실어 회신(ACK). 29바이트 all-zero 관측 = "빈 resPack" 가설과 정합
- `CMiniPCLauncher::UpdateInfo`(주기 상태 송신) / `CMiniPCLauncher::DoTask`(파일 전송 — 진행률/속도 로그 포함, 리소스/펌웨어 업데이트용)
- GUID 2개: `{780F2CEC-5710-43AF-83E5-94C97BAF7931}`, `{E3AA11A9-EFE9-469D-A007-058707CBA4BC}` — 디바이스 인터페이스 식별 후보
- 바이트 레벨 필드 구조는 Ghidra 디컴파일로 확정 중 → docs/protocol.md

### 커뮤니티 MCU측 분석 (교차 검증 3축)

- [r/ayaneo "The AYANEO AM02 subscreen customization"](https://www.reddit.com/r/ayaneo/comments/1isly3s/) — 하드웨어: Allwinner **F1C200s** + Buildroot Linux (SD 부트), tslib/framebuffer UI, `/data/app/minipc-screen-launcher`(GUI) + `/data/app/launcher-comm`(호스트 통신) 2데몬 구조
- vsoftster 댓글의 `minipc-screen-launcher` 역컴파일 — shareData 218B 스키마, 시간 1회 래치(`flag_5081`), cpu/gpu `{freq i, usage f, package f, temp i}` 확정. 상세 매핑은 [protocol.md](protocol.md)
