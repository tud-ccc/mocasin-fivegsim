# Copyright (C) 2020 TU Dresden
# Licensed under the ISC license (see LICENSE.txt)
#
# Authors: Julian Robledo


class Phybench(object):
    """Phybench application structure.

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
    num_slots = 2  # Number of slots per subframe - standard defined

    @staticmethod
    def get_num_micf(layers):
        """Get number of parallel kernels in phase micf.

        Subkernels: Matched filter + IFFT + Windowing + FFT.
        """
        return layers * Phybench.num_antenna

    @staticmethod
    def get_num_combwc():
        """Get number of parallel kernels in phase conbwc.

        Subkernels: Combiner weights.
        """
        return Phybench.SC

    @staticmethod
    def get_num_antcomb(layers):
        """Get number of parallel kernels in phase antcomb.

        Subkernels: Antenna Combinning + IFFT.
        """
        return layers * Phybench.num_symb

    @staticmethod
    def get_num_demap():
        """Get number of parallel kernels in phase demap.

        Subkernels: Deinterleaver + Soft symbol Demap.
        """
        return Phybench.SC * Phybench.num_slots
