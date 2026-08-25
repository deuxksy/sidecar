"""collect()가 hwmon name/label 기반으로 온도를 찾는지 검증 (가짜 sysfs 트리 사용)."""
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
