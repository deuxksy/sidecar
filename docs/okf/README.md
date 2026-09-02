# OKF (Open Knowledge Framework) 문서 허브

AYANEO AM-02 서브스크린의 하드웨어 특성, 통신 프로토콜 및 역설계 결과를 Diátaxis 4분면 체계로 정리한 기술 사양 허브입니다.

---

## Diátaxis 문서 체계

### 1. 참고자료 (Reference)
- [AM-02 서브스크린 직렬 프로토콜 (v2)](reference/protocol.md) — 253바이트 와이어 포맷, CRC32 LE 헤더, payload 필드 매핑 및 MCU RTC 래치 동작 명세

### 2. 설명 및 배경 (Explanation)
- [Phase 0 진단 결과 및 프로브 분석](explanation/phase0.md) — 네이티브 UART(/dev/ttyS0) 확인, 패시브 리슨 실험, AYASPACE 정적 역컴파일 및 F1C200s 펌웨어 분석
