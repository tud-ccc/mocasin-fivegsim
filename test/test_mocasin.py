# Copyright (C) 2021 TU Dresden
# All Rights Reserved
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
            "platform=maps_exynos",
            f"outdir={tmpdir}",
        ],
        cwd=tmpdir,
    )

    assert os.path.isfile(os.path.join(tmpdir, "best_time.txt"))
    assert os.path.isfile(os.path.join(tmpdir, "mapping.pickle"))


@pytest.mark.parametrize(
    "prbs,layers,mod,expected",
    [
        (4, 4, 1, "0.514811688 ms"),
        (10, 10, 2, "1.593689511 ms"),
        (32, 16, 4, "6.451352689 ms"),
    ],
)
def test_simulate(tmpdir, prbs, layers, mod, expected):
    res = subprocess.run(
        [
            "mocasin",
            "simulate",
            "platform=maps_exynos",
            "graph=phybench",
            "trace=phybench",
            "mapper=static_cfs",
            f"phybench.prbs={prbs}",
            f"phybench.layers={layers}",
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
