# Copyright (C) 2019 TU Dresden
# All Rights Reserved
#
# Authors: Julian Robledo


def get_task_time(tgff_name):
    """Read task execution time information on TGFF format
    and return a list of task times
    """
    proc_file = open(tgff_name, "r")
    lines = proc_file.readlines()
    lines = [x for x in lines if x.find("#") == -1]
    lines = [x.strip() for x in lines]
    lines = [x.split() for x in lines]
    lines = [x for x in lines if x != []]

    proc_list = list()
    task_list = {}

    while len(lines) > 0:
        line = lines.pop(0)
        if len(line) == 7:
            task_list[int(line[0])] = float(line[3])
        elif line[0].find("}") != -1:
            proc_list.append(task_list)
        elif line[0].find("@PROC") != -1:
            task_list = {}

    proc_file.close()
    return proc_list
