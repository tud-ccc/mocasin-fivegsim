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

    found_time_line = False
    found_miss_line = False
    stdout = res.stdout.decode()
    for line in stdout.split("\n"):
        if line.startswith("missrate = "):
            assert line == "missrate = 0.1111111111111111"
            found_miss_line = True
        if line.startswith("Total simulated time: "):
            time = line[22:]
            assert time == "31.0 ms"
            found_time_line = True

    assert found_miss_line
    assert found_time_line
