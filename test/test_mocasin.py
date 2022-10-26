# Copyright (C) 2021 TU Dresden
# Licensed under the ISC license (see LICENSE.txt)
#
# Authors: Christian Menard

import os
import pytest
import subprocess


def test_generate_mapping(tmpdir):
    subprocess.check_call(
        [
            "mocasin",
            "generate_mapping",
            "mapper=random",
            "graph=phybench",
            "trace=phybench",
            "platform=odroid",
            "platform.processor_0.type=ARM_CORTEX_A7",
            "platform.processor_1.type=ARM_CORTEX_A15",
            f"outdir={tmpdir}",
        ],
        cwd=tmpdir,
    )

    assert os.path.isfile(os.path.join(tmpdir, "best_time.txt"))
    assert os.path.isfile(os.path.join(tmpdir, "mapping.pickle"))


@pytest.mark.parametrize(
    "prbs,layers,antennas,mod,expected",
    [
        (4, 4, 4, 2, "0.367857126 ms"),
        (10, 10, 4, 4, "1.739934117 ms"),
        (32, 16, 4, 8, "9.83357471 ms"),
    ],
)
def test_simulate(tmpdir, prbs, layers, antennas, mod, expected):
    res = subprocess.run(
        [
            "mocasin",
            "simulate",
            "platform=odroid",
            "platform.processor_0.type=ARM_CORTEX_A7",
            "platform.processor_1.type=ARM_CORTEX_A15",
            "graph=phybench",
            "trace=phybench",
            "mapper=static_cfs",
            f"phybench.prbs={prbs}",
            f"phybench.layers={layers}",
            f"phybench.antennas={antennas}",
            f"phybench.modulation_scheme={mod}",
        ],
        cwd=tmpdir,
        check=True,
        stdout=subprocess.PIPE,
    )

    found_line = False
    stdout = res.stdout.decode()
    for line in stdout.split("\n"):
        if line.startswith("Total simulated time: "):
            time = line[22:]
            assert time == expected
            found_line = True

    assert found_line
