# Copyright (C) 2020 TU Dresden
# Licensed under the ISC license (see LICENSE.txt)
#
# Authors: Julian Robledo, Robert Khasanov

import numpy as np
import random
import sys
import csv


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

    with open(f"{file_path}/{file_name}.csv", "w") as tf_file:
        csv_writer = csv.writer(tf_file)
        csv_writer.writerow(['subframe', 'bs', 'ue', 'prbs', 'lay', 'mod', 'cri','is_new'])

        for s in range(1,sub+1):
            if s % period == 0:
                n = random.randint(0, max_ue)
                if n == 0:
                    csv_writer.writerow([s, '-', '-', '-', '-', '-', '-', '-'])
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
                    csv_writer.writerow([s, cnt, cnt, prb, lay, mod, cri, int(1)])
                cnt = 0
            else:
                csv_writer.writerow([s, '-', '-', '-', '-', '-', '-', '-'])


if __name__ == "__main__":
    iargs = tuple(int(x) for x in sys.argv[1:])
    main(*iargs)
