# Copyright (C) 2020 TU Dresden
# All Rights Reserved
#
# Authors: Julian Robledo


class Phybench(object):
    """
    - micf   : #Layers * #Antenna (#Antenna is base station parameter, so it
               would be independent of UE workload)
    - combwc : #SC (This may independent of UEs, but actor execution time is
               linearly related to #PRBs)
    - antcomb : #Layers x #Symbols (Again #Symbols is standard defined and
                independent of UE workload)
    - demap : #SC*2 (This may be independent of UEs, but actor execution time
              is linearly related to #PRBs and modulation scheme).
    """

    num_antenna = 4  # number of antennas - fixed to 4 for all base stations
    num_symb = 6  # number of symbols per slot - standard defined
    SC = 12  # Number of subCarriers per symbol - standard defined

    @staticmethod
    def get_num_micf(layers):
        """Calculate number of parallel kernels in phase micf (Matched filter +
        IFFT + Windowing + FFT)"""
        return layers * Phybench.num_antenna

    @staticmethod
    def get_num_combwc():
        """Get number of parallel kernels in phase conbwc (Combiner
        weights)"""
        return Phybench.SC

    @staticmethod
    def get_num_antcomb(layers):
        """Calculate number of parallel kernels in phase antcomb (Antenna
        Combinning + IFFT)"""
        return layers * Phybench.num_symb

    @staticmethod
    def get_num_demap():
        """Calculate number of parallel kernels in phase demap (Deinterleaver +
        Soft symbol Demap)"""
        return Phybench.SC * 2
