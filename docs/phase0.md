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
