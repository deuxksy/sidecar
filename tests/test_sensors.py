"""collect()가 hwmon name/label 기반으로 온도를 찾는지 검증 (가짜 sysfs 트리 사용)."""
import time
from pathlib import Path

from am02_subscreen.sensors import collect


def _make_hwmon(root: Path, n: int, name: str, labels: dict[str, int]):
    d = root / f"hwmon{n}"
    d.mkdir(parents=True)
    (d / "name").write_text(name)
    for i, (label, milli) in enumerate(labels.items(), start=1):
        (d / f"temp{i}_label").write_text(label)
        (d / f"temp{i}_input").write_text(str(milli))
    return d


def test_collect_reads_k10temp_tctl_and_amdgpu_edge(tmp_path):
    _make_hwmon(tmp_path, 0, "nvme", {"Composite": 40000})
    _make_hwmon(tmp_path, 1, "k10temp", {"Tctl": 44625, "Tdie": 44000})
    _make_hwmon(tmp_path, 2, "amdgpu", {"edge": 42000, "junction": 43500})

    metrics = collect(tmp_path)

    assert metrics["cpu_temp"] == 44.625
    assert metrics["gpu_temp"] == 42.0
    assert metrics["unix_ts"] > 0


def test_collect_returns_none_when_sensor_missing(tmp_path):
    _make_hwmon(tmp_path, 0, "nvme", {"Composite": 40000})

    metrics = collect(tmp_path)

    assert metrics["cpu_temp"] is None
    assert metrics["gpu_temp"] is None


def test_collect_includes_wall_clock_for_mcu_sync(tmp_path):
    """MCU RTC 동기화용 로컬 시각 — year≠0 첫 프레임에만 래치되므로 매 프레임 첨부."""
    before = time.localtime()
    metrics = collect(tmp_path)
    after = time.localtime()

    # collect 수행 전후 어느 쪽 시각과도 일치하면 통과 (경계 통과 허용)
    for key, attr in [("time_year", "tm_year"), ("time_month", "tm_mon"),
                      ("time_day", "tm_mday"), ("time_hour", "tm_hour"),
                      ("time_minute", "tm_min"), ("time_second", "tm_sec")]:
        assert metrics[key] in {getattr(before, attr), getattr(after, attr)}
    # wire 요일은 0=Sunday — 파이썬 tm_wday(0=Monday) 변환 (실기 2026-08-25 "Tuesday" 렌더 검증)
    assert metrics["time_dow"] in {(before.tm_wday + 1) % 7, (after.tm_wday + 1) % 7}
    assert metrics["time_year"] >= 2000  # year≠0 — MCU 래치 조건
