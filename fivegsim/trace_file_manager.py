# Copyright (C) 2020 TU Dresden
# All Rights Reserved
#
# Authors: Julian Robledo

class TraceFileManager():
    """ Allows navigation along a LTE trace file with the following format:    
    <number of UE>
    [<base station ID> <CRNTI> <number of PRBs> <number of layers> <modulation scheme> <UE Criticality Type> <is New>]
    [<base station ID> <CRNTI> <number of PRBs> <number of layers> <modulation scheme> <UE Criticality Type> <is New>]
    [<base station ID> <CRNTI> <number of PRBs> <number of layers> <modulation scheme> <UE Criticality Type> <is New>]
    ---------- <Subframe Number>
    """
    def __init__(self, TF_name):
        self.TF_name = TF_name
        self.TF_file = open(self.TF_name, "r")

        self.TF_current_subframe = 0            # Current subframe Id
        self.TF_current_subf_size = 0           # Size of current subframe

        self.TF_error = False                   # Error
        self.TF_EOF = False                     # End of File

    class Trace():
        """ Represents a single LTE trace.
        """
        def __init__(self,
                     base_station_id = None,
                     CRNTI = None,
                     PRBs = None,
                     layers = None,
                     modulation_scheme = None,
                     UE_criticality = None,
                     is_CRNTI_new = None):
            self.base_station_id = base_station_id          # Base Station Identifier which serves the UE
            self.CRNTI = CRNTI                              # A kind of UE Identifier
            self.PRBs = PRBs                                # The number of physical resource blocks allocated to the UE
            self.layers =  layers                           # The number of (independent) layers of communication
            self.modulation_scheme =  modulation_scheme     # Modulation scheme
            self.UE_criticality = UE_criticality            # UE Traffic type
            self.is_CRNTI_new = is_CRNTI_new                # Is CRNTI seen before for [No/Yes] ?

    class Subframe():
        """ Represents a LTE subframe containing a collection of LTE traces.
        """
        def __init__(self, subf_id = None):
            self.trace = list()
            self.id = subf_id

        def add_trace(self, trace):
            self.trace.append(trace) # Add new trace to subframe

        def set_id(self, sid):
            self.id = sid

    def get_all_subframes(self):
        """ Reads the whole file and returns a list of Subframe objects 
        containing all LTE subframes contained in file
        """
        subframe_list = list()
        while True:
            subframe = self.get_next_subframe()
            if (not self.TF_EOF and not self.TF_error):
                subframe_list.append (subframe)
            else:
                break

        return subframe_list

    def get_next_subframe(self):
        """ search for next subframe into the file and returns Subframe object with the whole subframe
        """
        subframe = self.Subframe()
        TF_current_trace = 0

        # Find new frame
        while True:
            line = self.TF_file.readline()
            if line == "": 
                self.TF_EOF = True
                break
            line = line.strip()
            line = line.split()

            # new frame recognized
            if len(line) == 1:            
                self.TF_current_subf_size = int(line[0])
                break
            # empty line
            elif len(line) == 0: 
                pass
            # error
            else:
                # Expected new frame
                self.TF_error = True
                break

        if self.TF_current_subf_size != 0:
            # Read all traces in subframe
            while True:
                line = self.TF_file.readline()

                #End of file
                if line == "": 
                    self.TF_EOF = True
                    break

                line = line.strip()
                line = line.split()

                # find LTE trace
                if len(line) == 7:          
                    TF_current_trace += 1
                    line = [int(i) for i in line]   # cast string to int
                    ntrace = self.Trace(line[0], 
                                        line[1], 
                                        line[2], 
                                        line[3], 
                                        line[4], 
                                        line[5], 
                                        line[6])
                    # Add trace to subframe
                    subframe.add_trace(ntrace)
                # empty line
                elif len(line) == 0: 
                    pass
                # error
                else:
                    # Expected LTE trace
                    self.TF_error = True
                    break

                if TF_current_trace == self.TF_current_subf_size:
                    break

        # find end of subframe
        while True:
            line = self.TF_file.readline()
            if line == "": 
                self.TF_EOF = True
                break
            line = line.strip()
            line = line.split()

            # end of subframe
            if len(line) == 2:          
                if line[0].find('-') != -1:
                    line = line.pop(1)
                    subframe.set_id(int(line))
                    break
            # empty line
            elif len(line) == 0: 
                pass
            # error
            else:
                # Expected end of frame
                self.TF_error = True
                break

        return subframe
