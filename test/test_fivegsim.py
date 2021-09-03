# Copyright (C) 2021 TU Dresden
# Licensed under the ISC license (see LICENSE.txt)
#
# Authors: Robert Khasanov, Christian Menard

from pathlib import Path
import pytest
import subprocess


@pytest.mark.parametrize(
    "trace,platform,runtime,total,rejected,missed,simulated",
    [
        ("lte_trace_1.txt", "odroid", "None", 18, 0, 2, 31.0),
        ("lte_trace_2.txt", "odroid", "None", 18, 0, 12, 11.0),
        ("lte_trace_2.txt", "odroid_acc", "None", 18, 0, 12, 11.0),
        ("lte_trace_1.txt", "odroid_acc", "load_balancer", 18, 0, 2, 31.0),
        ("lte_trace_2.txt", "odroid", "load_balancer", 18, 0, 10, 11.0),
        ("lte_trace_2.txt", "odroid_acc", "load_balancer", 18, 0, 5, 11.0),
        ("lte_trace_1.txt", "odroid_acc", "tetris", 18, 2, 0, 31.0),
        ("lte_trace_2.txt", "odroid", "tetris", 18, 7, 0, 11.36),
        ("lte_trace_2.txt", "odroid_acc", "tetris", 18, 6, 0, 11.40),
    ],
)
def test_fivegsim(
    tmpdir, trace, total, platform, runtime, rejected, missed, simulated
):
    trace_file = Path(__file__).parent.resolve().joinpath(trace)

    cmd = ["fivegsim", f"trace_file={trace_file}", f"platform={platform}"]
    if runtime == "load_balancer":
        cmd.append("load_balancer=true")
    elif runtime == "tetris":
        cmd.append("mapper=fiveg")
        cmd.append("tetris_runtime=true")
        if platform == "odroid":
            cmd.append("pareto_time_scale=1.09")
            cmd.append("pareto_time_offset=0.10")
        elif platform == "odroid_acc":
            cmd.append("pareto_time_scale=1.05")
            cmd.append("pareto_time_offset=0.24")
    else:
        assert runtime == "None"

    res = subprocess.run(cmd, cwd=tmpdir, check=True, stdout=subprocess.PIPE)

    found_lines = 0x0
    stdout = res.stdout.decode()
    for line in stdout.split("\n"):
        if line.startswith("Total applications: "):
            test_total = int(line[20:])
            assert test_total == total
            found_lines |= 0x1
        if line.startswith("Total rejected: "):
            test_rejected = int(line[16:])
            assert test_rejected == rejected
            found_lines |= 0x2
        if line.startswith("Missed deadline: "):
            test_missed = int(line[17:])
            assert test_missed == missed
            found_lines |= 0x4
        if line.startswith("Total simulated time: "):
            test_simulated = float(line[22:].split()[0])
            assert abs(test_simulated - simulated) < 0.01
            found_lines |= 0x8

    assert found_lines == 0xF
