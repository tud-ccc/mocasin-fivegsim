# Copyright (C) 2020 TU Dresden
# Licensed under the ISC license (see LICENSE.txt)
#
# Authors: Julian Robledo

import csv


def get_task_time(tgff_name):
    """Read task execution time from TGFF and return a list of task times."""
    proc_latencies = {}
    with open(tgff_name) as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            if row["kernel"] not in proc_latencies:
                proc_latencies[row["kernel"]] = {}
            if row["proc"] not in proc_latencies[row["kernel"]]:
                proc_latencies[row["kernel"]][row["proc"]] = {}
            if row["mod_scheme"] != "NA":
                if (
                    int(row["mod_scheme"])
                    not in proc_latencies[row["kernel"]][row["proc"]]
                ):
                    proc_latencies[row["kernel"]][row["proc"]][
                        int(row["mod_scheme"])
                    ] = {}
                proc_latencies[row["kernel"]][row["proc"]][
                    int(row["mod_scheme"])
                ][int(row["prbs"])] = float(row["cc"])
            else:
                proc_latencies[row["kernel"]][row["proc"]][
                    int(row["prbs"])
                ] = float(row["cc"])

    return proc_latencies
