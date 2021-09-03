# Copyright (C) 2020 TU Dresden
# Licensed under the ISC license (see LICENSE.txt)
#
# Authors: Julian Robledo, Robert Khasanov

import numpy as np
import random
import sys


def main(sub=600, median_prbs=10, max_ue=3, period=1):
    """Random LTE traces generator.

    This function generates an output file containing a set of LTE subframes.
    The file follows the following pattern: each subframe contains a random
    number of UE with random modulation scheme, criticality and number of prbs.
    Subframes are generated once per period, in between they filled with empty
    subframes. Note that the generated subframe could contain a zero number of
    UEs.

    sub: total number of subframes to generate, counting also empty subframes.
    median_prbs: median of the non-uniform random distribution to calculate
    number of prbs, should be <= 100.
    max_ue: max number of UE per subframe, the min is set to 1.
    period: a period of generated subframes, default is 1.
    """
    file_path = "."
    file_name = "lte_traces"
    cnt = 0

    with open(f"{file_path}/{file_name}.txt", "w") as tf_file:
        for s in range(sub):
            if s % period == 0:
                n = random.randint(0, max_ue)
                tf_file.write(f"{n}\n")

                for ue in range(n):
                    while True:
                        prb = np.random.poisson(median_prbs)
                        if prb < 100:
                            break
                    mod = random.randint(0, 4)
                    lay = 4
                    cri = random.randint(0, 2)
                    if cri == 1:
                        cri = random.randint(0, 2)  # reduce probability of 1
                    cnt += 1
                    tf_file.write(f"{cnt} {cnt} {prb} {lay} {mod} {cri} 1\n")
                cnt = 0
            else:
                tf_file.write("0\n")
            tf_file.write(f"---------- {s+1}\n")


if __name__ == "__main__":
    iargs = tuple(int(x) for x in sys.argv[1:])
    main(*iargs)
