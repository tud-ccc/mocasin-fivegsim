# Copyright (C) 2021 TU Dresden
# All Rights Reserved
#
# Authors: Christian Menard

import os
import subprocess


def test_fivegsim(tmpdir):
    trace_file = os.path.join(os.path.dirname(__file__), "test_trace.txt")

    res = subprocess.run(
        ["fivegsim", f"trace_file={trace_file}"],
        cwd=tmpdir,
        check=True,
        stdout=subprocess.PIPE,
    )

    found_lines = 0x0
    stdout = res.stdout.decode()
    for line in stdout.split("\n"):
        if line.startswith("Total applications: "):
            total = line[20:]
            assert total == "18"
            found_lines |= 0x1
        if line.startswith("Missed deadline: "):
            missed = line[17:]
            assert missed == "5"
            found_lines |= 0x2
        if line.startswith("Total simulated time: "):
            time = line[22:]
            assert time == "31.0 ms"
            found_lines |= 0x4

    assert found_lines == 0x7
