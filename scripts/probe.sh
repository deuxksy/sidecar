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
