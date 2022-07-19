# Copyright (C) 2020 TU Dresden
# Licensed under the ISC license (see LICENSE.txt)
#
# Authors: Julian Robledo

from scipy import stats
from collections import OrderedDict
import csv

def get_task_time(tgff_name):
    """Read task execution time from TGFF and return a list of task times."""
    proc_latencies = {}
    with open(tgff_name) as csvfile:
        reader = csv.reader(csvfile)
        next(reader) # headers
        reader = list(reader)
        for row in reader:
            if row[1] not in proc_latencies:
                proc_latencies[row[1]] = {}
            if row[0] not in proc_latencies[row[1]]:
                proc_latencies[row[1]][row[0]] = {}
            if row[4] != 'NA':
                if int(row[4]) not in proc_latencies[row[1]][row[0]]:
                    proc_latencies[row[1]][row[0]][int(row[4])] = {}
                proc_latencies[row[1]][row[0]][int(row[4])][int(row[2])] = float(row[3])
            else:
                proc_latencies[row[1]][row[0]][int(row[2])] = float(row[3])

    return proc_latencies


# split kernel latencies, create a sublist for every kernel
#kernel_latencies = list()
#for p in range(0, len(all_kernels), 100):
#    kernel_latencies.append(all_kernels[p:p+100])

# calculate linear regression for every kernel
#proc_fn = {0:OrderedDict(), 1:OrderedDict()}
#prbs = list(range(1, 101))

# processor 0
#for l, k in zip(kernel_latencies[:10], kernel_names):
#    proc_fn[0][k] = stats.linregress(prbs, l)

# processor 1
#for l, k in zip(kernel_latencies[10:], kernel_names):
#    proc_fn[1][k] = stats.linregress(prbs, l)

# fft kernels cannot be modeled as a linear regression
#proc_fn[0]["fft"] = [
#    [16, kernel_latencies[1][0]],
#    [32, kernel_latencies[1][1]],
#    [64, kernel_latencies[1][2]],
#    [128, kernel_latencies[1][5]],
#    [256, kernel_latencies[1][10]],
#    [512, kernel_latencies[1][21]],
#    [1024, kernel_latencies[1][50]],
#    [2048, kernel_latencies[1][85]],
#]
#proc_fn[1]["fft"] = [
#    [16, kernel_latencies[11][0]],
#    [32, kernel_latencies[11][1]],
#    [64, kernel_latencies[11][2]],
#    [128, kernel_latencies[11][5]],
#    [256, kernel_latencies[11][10]],
#    [512, kernel_latencies[11][21]],
#    [1024, kernel_latencies[11][50]],
#    [2048, kernel_latencies[11][85]],
#]


#import matplotlib.pyplot as plt
#def myfunc(prbs, slope, intercept):
#    return slope * prbs + intercept

#def pp(mymodel, n):
#    plt.scatter(prbs, n)
#    plt.plot(prbs, mymodel, color='red')
#    plt.show()

#proc = proc_fn[1]["fft"]
#lat = kernel_latencies[11]
#mymodel = list()

#for i in prbs:
#    mymodel.append(myfunc(i, proc.slope, proc.intercept))
#pp(mymodel, lat)

# prbs2 = [1, 2, 3, 6, 11, 22, 51, 86]