# Copyright (C) 2020 TU Dresden
# All Rights Reserved
#
# Authors: Julian Robledo

#from enum import Enum

#class LTE_modulation_scheme(Enum):
#    PSK = 0
#    QPSK = 1
#    QAM16 = 2
#    QAM64 = 3
#    
#class LTE_traffic_type(Enum):
#    IOT = 0
#    AVT = 1     # most critical traffic
#    EMBB = 2    # least critical traffic

class LTE(object):
    """ LTE parameters - uplink communication
    """
    num_antenna = 4         # fix to 4 for all base stations
    num_symb = 6            # number of symbols - standard defined
    SC = 12                 # SubCarriers - standard defined
       
class PHY(object):    
    """
    - micf   : #Layers * #Antenna (#Antenna is base station parameter, so it would be independent of UE workload)
    - combwc : 12 (This may independent of UEs, but actor execution time is linearly related to #PRBs)
    - antcomb : #Layers x #Symbols (Again #Symbols is standard defined and independent of UE workload)
    - demap : 24 (This may be independent of UEs, but actor execution time is linearly related to #PRBs and modulation scheme).
    """   

    @staticmethod
    def get_num_micf(layers):
        """ Calculate number of parallel actors in phase micf (Matched filter + IFFT + Windowing + FFT)
        """
        return layers * LTE.num_antenna
        
    @staticmethod
    def get_num_combwc():
        """ Calculate number of parallel actors in phase conbwc (Combiner weights)
        """
        return 12
        
    @staticmethod
    def get_num_antcomb(layers):
        """ Calculate number of parallel actors in phase antcomb (Antenna Combinning + IFFT)
        """
        return layers * LTE.num_symb
        
    @staticmethod
    def get_num_demap():
        """ Calculate number of parallel actors in phase demap (Deinterleaver + Soft symbol Demap)
        """
        return 24
