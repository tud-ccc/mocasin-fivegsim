# Copyright (C) 2020 TU Dresden
# Licensed under the ISC license (see LICENSE.txt)
#
# Authors: Julian Robledo


class TraceFileManager:
    """Trace file manager.

    Allows navigation along a LTE trace file with the following format:
    subframe, base station ID, CRNTI, number of PRBs, number of layers, modulation scheme, UE Criticality Type, is New
    """

    def __init__(self, TF_name):
        self.TF_name = TF_name
        self.TF_file = open(self.TF_name, "r")

        self.TF_current_line = self.TF_file.readline() # pop headers line
        self.TF_current_line = self.TF_file.readline() # get first line

        self.TF_current_subframe = 1
        self.TF_EOF = False  # End of File

    class Trace:
        """Represents a single LTE trace."""

        def __init__(
            self,
            base_station_id=None,
            CRNTI=None,
            PRBs=None,
            layers=None,
            modulation_scheme=None,
            UE_criticality=None,
            is_CRNTI_new=None,
        ):
            # Base Station Identifier which serves the UE
            self.base_station_id = base_station_id
            # A kind of UE Identifier
            self.CRNTI = CRNTI
            # The number of physical resource blocks allocated to the UE
            self.PRBs = PRBs
            # The number of (independent) layers of communication
            self.layers = layers
            # Modulation scheme
            self.modulation_scheme = modulation_scheme
            # UE Traffic type
            self.UE_criticality = UE_criticality
            # Is CRNTI seen before for [No/Yes] ?
            self.is_CRNTI_new = is_CRNTI_new

    class Subframe:
        """Represents a LTE subframe containing a collection of LTE traces."""

        def __init__(self, subf_id=None):
            self.trace = list()
            self.id = subf_id

        def add_trace(self, trace):
            self.trace.append(trace)  # Add new trace to subframe

        def set_id(self, sid):
            self.id = sid

    def get_all_subframes(self):
        """Get all subframes.

        Reads the whole file and returns a list of Subframe objects containing
        all LTE subframes contained in file.
        """
        subframe_list = list()
        while True:
            subframe = self.get_next_subframe()
            subframe_list.append(subframe)
            if self.TF_EOF:
                break

        return subframe_list

    def get_next_subframe(self):
        """Get next subframe.

        Search for next subframe into the file and returns Subframe object with
        the whole subframe.
        """
        subframe = self.Subframe()

        # Find new subframe
        while True:
            line = self.TF_current_line
            if line == "":
                self.TF_EOF = True
                line = [self.TF_current_subframe]
            else:
                line = line.strip()
                line = line.split(",")

            # new subframe recognized
            if int(line[0]) != self.TF_current_subframe or self.TF_EOF:
                subframe.set_id(int(line[0]) - 1)
                self.TF_current_subframe = int(line[0])
                break

            # Read all traces in subframe
            if line[1] == "-": # empty subframe
                pass
            else: # Add trace to subframe
                iline = tuple(int(i) for i in line[1:])  # cast string to int
                ntrace = self.Trace(*iline)
                subframe.add_trace(ntrace)

            self.TF_current_line = self.TF_file.readline()

        return subframe
