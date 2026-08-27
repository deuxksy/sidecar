#!/usr/bin/env bash
# ttyS0 프로브: 패시브 리슨 / 페이로드 송신 후 수신 / 프로토콜 프레임 송신.
# 사용: sudo ./scripts/probe.sh {listen [초] [baud] | probe [초] [baud] [payload] | frame [cmd] | demo}
#   listen — 송신 없이 수신만 (MCU 자발 송신 확인)
#   probe  — payload 송신(기본 'T=45\n', octal escape 지원: \0377 = 0xff) 후 초만큼 수신
#   frame  — 프로토콜 검증: payload 249B(cmd@0, 나머지 0) + zlib CRC32 → 253B 송신,
#            응답 첫 4바이트가 송신 CRC와 같은지 검증 (docs/okf/reference/protocol.md)
# 판별: 응답이 baud에 정비례하며 항상 0x00이면 break pulse,
#       baud 변경 시 garbage가 나오면 실제 데이터.
set -euo pipefail
PORT=/dev/ttyS0
cmd="${1:-listen}"
secs="${2:-5}"
baud="${3:-115200}"
payload="${4:-T=45\\n}"
stty -F "$PORT" "$baud" raw -echo -echoe -echok
case "$cmd" in
  listen)
    echo "[*] ${secs}초 패시브 리슨 ($PORT ${baud}) — 수신 바이트 수:"
    timeout "$secs" dd if="$PORT" bs=1 2>/dev/null | tee /tmp/probe-rx.bin | od -A x -t x1z || true
    echo "[*] bytes: $(wc -c < /tmp/probe-rx.bin)" ;;
  probe)
    if [[ "$payload" == @* ]]; then
      # @file — 파일 내용을 그대로 송신 (바이너리 payload 실험)
      src="${payload#@}"
      echo "[*] baud=${baud} file=$src ($(wc -c < "$src")B) 송신 후 ${secs}초 수신:"
      cat "$src" > "$PORT"
    else
      echo "[*] baud=${baud} payload='$(printf '%b' "$payload" | od -A n -t x1 | tr -s ' \n' ' ')' 송신 후 ${secs}초 수신:"
      printf '%b' "$payload" > "$PORT"
    fi
    timeout "$secs" dd if="$PORT" bs=1 2>/dev/null | tee /tmp/probe-rx.bin | od -A x -t x1z || true
    echo "[*] bytes: $(wc -c < /tmp/probe-rx.bin)" ;;
  frame)
    frame_cmd="${2:-1}"
    python3 - "$frame_cmd" <<'PYEOF'
import struct, sys, zlib
p = bytearray(249)
p[0] = int(sys.argv[1], 0)
crc = zlib.crc32(bytes(p)) & 0xffffffff
# wire format: [CRC32 4B LE][payload 249B] — CRC가 프레임 앞 (Ghidra 스택 주소 역산)
open('/tmp/probe-tx.bin', 'wb').write(struct.pack('<I', crc) + bytes(p))
print(f"[*] cmd={p[0]} crc32={crc:08x} frame=253B (CRC prepend)")
PYEOF
    echo "[*] 프레임 송신 후 5초 수신:"
    cat /tmp/probe-tx.bin > "$PORT"
    timeout 5 dd if="$PORT" bs=1 2>/dev/null | tee /tmp/probe-rx.bin | od -A x -t x1z || true
    n=$(wc -c < /tmp/probe-rx.bin)
    echo "[*] bytes: $n"
    if [ "$n" -ge 4 ]; then
      python3 - <<'PYEOF'
import zlib, struct
tx = open('/tmp/probe-tx.bin', 'rb').read()
rx = open('/tmp/probe-rx.bin', 'rb').read()
want = struct.pack('<I', zlib.crc32(tx[4:253]) & 0xffffffff)
print(f"[*] rx[0:4]={rx[:4].hex()} expected={want.hex()} → {'MATCH - 링크 확립' if rx[:4] == want else 'MISMATCH'}")
PYEOF
    fi ;;
  demo)
    # 필드 매핑 시각 실험: 구별값 주입한 cmd=2 프레임을 반복 송신.
    # 화면 표시 위치로 payload 필드 순서 확정 (docs/okf/reference/protocol.md 미확인 #1)
    demo_n="${2:-10}"
    demo_iv="${3:-400}"
    python3 - <<'PYEOF'
import struct, zlib, time, datetime
p = bytearray(249)
p[0] = 2                                        # cmd=2 상태 갱신
# cpu/gpu 블록: {freq i32, usage f32, package f32, temp i32} — 커뮤니티 MCU 코드로 확정
struct.pack_into('<i', p, 29, 3100)             # cpu freq MHz
struct.pack_into('<f', p, 33, 22.0)             # cpu usage %
struct.pack_into('<f', p, 37, 8.25)             # cpu package W
struct.pack_into('<i', p, 41, 44)               # cpu temp °C
struct.pack_into('<i', p, 45, 2800)             # gpu freq MHz
struct.pack_into('<f', p, 49, 66.0)             # gpu usage %
struct.pack_into('<f', p, 53, 9.5)              # gpu package W
struct.pack_into('<i', p, 57, 88)               # gpu temp °C
struct.pack_into('<i', p, 61, 1234)             # ram used MB
struct.pack_into('<i', p, 65, 5678)             # ram total MB
struct.pack_into('<i', p, 69, 999)              # ssd used
struct.pack_into('<i', p, 73, 1111)             # ssd total
struct.pack_into('<i', p, 81, 66)               # fan
struct.pack_into('<f', p, 85, 15.0)             # tdp cur — "FPT:0" 관측으로 float 가설 검증
p[117] = 1                                      # is24Hour (@118 style=0 유지 — 다른 스타일로 전환됨)
now = datetime.datetime.now()                   # 실제 KST — 첫 프레임에 MCU RTC 래치(1회)
p[119:127] = struct.pack('<H6B', now.year, now.month, now.day,
                         (now.weekday() + 1) % 7, now.hour, now.minute, now.second)
crc = zlib.crc32(bytes(p)) & 0xffffffff
open('/tmp/probe-tx.bin', 'wb').write(struct.pack('<I', crc) + bytes(p))
print(f"[*] demo 프레임: cpu {3100}/{22.0}/{8.25}/{44} gpu {2800}/{66.0}/{9.5}/{88} "
      f"ram 1234/5678 ssd 999/1111 fan 66 tdp 15 clock {now:%H:%M:%S} crc={crc:08x}")
PYEOF
    for i in $(seq 1 "$demo_n"); do
      cat /tmp/probe-tx.bin > "$PORT"
      timeout 1 dd if="$PORT" bs=1 2>/dev/null > /tmp/probe-rx.bin || true
      n=$(wc -c < /tmp/probe-rx.bin)
      echo "[*] frame $i/$demo_n → rx $n bytes"
      sleep "$(awk -v iv="$demo_iv" 'BEGIN{printf "%.2f", iv/1000}')"
    done ;;
  *)
    echo "usage: probe.sh {listen [초] [baud] | probe [초] [baud] [payload] | frame [cmd] | demo}" >&2
    exit 1 ;;
esac
