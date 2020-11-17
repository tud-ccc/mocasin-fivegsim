# Copyright (C) 2020 TU Dresden
# All Rights Reserved
#
# Authors: Julian Robledo
import sys
import random
import numpy as np
#from numpy import random

def main(sub = 600, median_prbs = 10, max_ue = 3):
    """ Random LTE traces generator
    
    this function generates an output file containing a set of LTE subframes.
    The file follows the following pattern: 1 subframe containing a random
    number of UE with random modulation scheme, criticality and number of prbs,
    followed by two empty subframes (zero UE).
    
    sub: total number of subframes to generate, counting also empty subframes.
    median_prbs: median of the non-uniform random distribution to calculate 
    number of prbs, should be <= 100.
    max_ue: # max number of UE per subframe, the min is set to 1.
    """

    file_path= '.'
    file_name= 'lte_traces'
    cnt = 0

    TF_file = open(file_path + '/' + file_name + ".txt", "w")
    for s in range(sub):
        if s%3 == 0:
            n = random.randint(1,max_ue)
            TF_file.write (str(n) + "\n")
            
            for ue in range(n):
                while True:
                    prb = np.random.poisson(median_prbs)
                    if prb < 100: break
                mod = random.randint(0,4)
                lay = 4
                cri = random.randint(0,2)
                if cri == 1: cri = random.randint(0,2) #reduce probability of 1
                cnt += 1
                TF_file.write (str(cnt) + " " + 
                               str(cnt) + " " + 
                               str(prb) + " " + 
                               str(lay) + " " +
                               str(mod) + " " +
                               str(cri) + " " +
                               str(1) +
                               "\n")
            cnt = 0
        else:
            TF_file.write (str(0) + "\n")
        TF_file.write("---------- " + str(s + 1) + "\n")
    TF_file.close()

if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]))