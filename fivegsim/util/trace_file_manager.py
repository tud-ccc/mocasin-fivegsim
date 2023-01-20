# Copyright (C) 2020 TU Dresden
# Licensed under the ISC license (see LICENSE.txt)
#
# Authors: Julian Robledo

import pandas as pd


class TraceFileManager:
    """Trace file manager.

    Allows navigation along a LTE trace file with the following format:
    subframe, base station ID, CRNTI, number of PRBs, number of layers, modulation scheme, UE Criticality Type
    """

    def __init__(self, TF_name):
        self.TF_name = TF_name
        self.TF_subframes = self.get_all_subframes()
        self.TF_next_subframe = 0
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

        all_subframes = pd.read_csv(self.TF_name)
        num_subframes = all_subframes["subframe"].max()

        # separated lists for every subframe
        subframes = list()
        for s in range(1, num_subframes + 1):
            subframe = self.Subframe()
            subframe.set_id(s)
            subf = all_subframes.query("subframe == @s")

            for index, row in subf.iterrows():
                if row.isnull().values.any():
                    break
                else:
                    iline = tuple(int(i) for i in row[1:])
                    ntrace = self.Trace(*iline)
                    subframe.add_trace(ntrace)
            subframes.append(subframe)

        return subframes

    def get_next_subframe(self):
        """Get next subframe.

        Search for next subframe in list of subframes returns Subframe object with
        the whole subframe.
        """
        if len(self.TF_subframes) > self.TF_next_subframe:
            subframe = self.TF_subframes[self.TF_next_subframe]
            self.TF_next_subframe += 1
        else:
            subframe = self.Subframe()
            self.TF_EOF = True

        return subframe
