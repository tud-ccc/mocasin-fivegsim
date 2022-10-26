# Copyright (C) 2020 TU Dresden
# Licensed under the ISC license (see LICENSE.txt)
#
# Authors: Julian Robledo

import csv


def get_task_time(tgff_name):
    """Read task execution time from TGFF and return a list of task times."""
    proc_latencies = {}
    with open(tgff_name) as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # headers
        reader = list(reader)
        for row in reader:
            if row[0] not in proc_latencies:
                proc_latencies[row[0]] = {}
            if row[1] not in proc_latencies[row[0]]:
                proc_latencies[row[0]][row[1]] = {}
            if row[4] != "NA":
                if int(row[4]) not in proc_latencies[row[0]][row[1]]:
                    proc_latencies[row[0]][row[1]][int(row[4])] = {}
                proc_latencies[row[0]][row[1]][int(row[4])][
                    int(row[2])
                ] = float(row[3])
            else:
                proc_latencies[row[0]][row[1]][int(row[2])] = float(row[3])

    return proc_latencies
