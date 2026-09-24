import os
import subprocess
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "bazzite/wait-time-sync.sh"


@pytest.mark.parametrize(
    ("mode", "expected_calls"),
    [("immediate", 1), ("delayed", 2), ("never", 60), ("error", 60)],
)
def test_wait_time_sync(tmp_path, mode, expected_calls):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    counter = tmp_path / "calls"
    timedatectl = bin_dir / "timedatectl"
    timedatectl.write_text(
        '#!/bin/sh\n'
        'n=$(cat "$TEST_COUNTER" 2>/dev/null || printf 0)\n'
        'n=$((n + 1))\n'
        'printf "%s" "$n" > "$TEST_COUNTER"\n'
        'if [ "$TEST_MODE" = error ]; then exit 1; fi\n'
        'if [ "$TEST_MODE" = immediate ] || '
        '{ [ "$TEST_MODE" = delayed ] && [ "$n" -ge 2 ]; }; then\n'
        '  printf "yes\\n"\n'
        'else\n'
        '  printf "no\\n"\n'
        'fi\n'
    )
    timedatectl.chmod(0o755)
    sleep = bin_dir / "sleep"
    sleep.write_text("#!/bin/sh\nexit 0\n")
    sleep.chmod(0o755)
    env = os.environ | {
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "TEST_COUNTER": str(counter),
        "TEST_MODE": mode,
    }
    result = subprocess.run(["bash", str(SCRIPT)], env=env, timeout=10)
    assert result.returncode == 0
    assert int(counter.read_text()) == expected_calls
