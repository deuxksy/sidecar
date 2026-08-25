"""AM02 시스템 정보 수집 — hwmon name/label 기반 (hwmon 번호는 부팅마다 변동)."""
import time
from pathlib import Path


def read_temperature(hwmon_root: Path, chip: str, label: str) -> float | None:
    """name==chip인 hwmon에서 temp*_label==label인 온도(°C) 반환. 못 찾으면 None."""
    for hwmon in sorted(hwmon_root.glob("hwmon*")):
        if (hwmon / "name").read_text().strip() != chip:
            continue
        for label_file in sorted(hwmon.glob("temp*_label")):
            if label_file.read_text().strip() == label:
                input_file = hwmon / f"{label_file.name.removesuffix('_label')}_input"
                raw = int(input_file.read_text())
                return raw / 1000.0
    return None


def collect(hwmon_root: Path = Path("/sys/class/hwmon")) -> dict:
    metrics = {
        "cpu_temp": read_temperature(hwmon_root, "k10temp", "Tctl"),
        "gpu_temp": read_temperature(hwmon_root, "amdgpu", "edge"),
        "unix_ts": time.time(),
    }
    # 로컬 시각 — MCU는 year≠0인 첫 프레임에만 RTC를 동기화하고 이후 무시하므로
    # 매 프레임 실어도 무해하고, 데몬 시작 프레임이 곧 동기화 프레임이 된다
    now = time.localtime()
    metrics.update({
        "time_year": now.tm_year, "time_month": now.tm_mon, "time_day": now.tm_mday,
        "time_dow": (now.tm_wday + 1) % 7,  # 파이썬 0=Monday → wire 0=Sunday
        "time_hour": now.tm_hour, "time_minute": now.tm_min, "time_second": now.tm_sec,
    })
    return metrics
