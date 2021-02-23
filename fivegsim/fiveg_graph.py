# Copyright (C) 2021 TU Dresden
# All Rights Reserved
#
# Authors: Julian Robledo, Christian Menard

from mocasin.common.graph import DataflowGraph, DataflowProcess, DataflowChannel
from fivegsim.phybench import PHY
from fivegsim.phybench import LTE

class FivegGraph(DataflowGraph):
    """The Dataflow graph of a 5G application

    The 5G application has the following type of tasks:
    micf, combwc, antcomb, demap.
    """

    def __init__(self, i, ntrace):
        super().__init__(f"fiveg{i}")

        prbs = ntrace.PRBs
        mod = ntrace.modulation_scheme
        lay = ntrace.layers
        ant = LTE.num_antenna
        sc = LTE.SC
        data_size = 4  # bytes
        nmbSc = prbs * sc

        if mod == 0:
            mod = 1
        elif mod == 1:
            mod = 2
        elif mod == 2:
            mod = 8
        elif mod == 3:
            mod = 12
        elif mod == 4:
            mod = 16

        num_phase1 = PHY.get_num_micf(ntrace.layers)
        num_phase2 = PHY.get_num_combwc()
        num_phase3 = PHY.get_num_antcomb(ntrace.layers)
        num_phase4 = PHY.get_num_demap()

        # kernels: name, number of instances
        kern = {
            "input" : 1,
            "mf" : num_phase1,
            "ifft1" : num_phase1,
            "wind" : num_phase1,
            "fft" : num_phase1,
            "comb" : num_phase2,
            "ant" : num_phase3,
            "ifft2" : num_phase3,
            "demap" : num_phase4,
            "output" : 1
        }

        # connections: origin, destination, token size
        connections = [
              ["input", "mf", data_size * nmbSc],
              ["input", "ant", data_size * nmbSc * lay],
              ["mf", "ifft1", data_size * nmbSc],
              ["ifft1", "wind", data_size * nmbSc],
              ["wind", "fft", data_size * nmbSc],
              ["fft", "comb", data_size * nmbSc],
              ["comb", "ant", data_size * prbs * ant],
              ["ant", "ifft2", data_size * prbs * ant],
              ["ifft2", "demap", data_size * prbs],
              ["demap", "output", data_size * prbs * mod],
        ]

        # add processes
        kernels = {}
        for k in kern:
            for n in range(kern[k]):
                process_name = k + str(n)
                kernels[process_name] = DataflowProcess(process_name)

        # add channels and connect processes
        channels = {}
        for conn in connections:
            for p1 in range(kern[conn[0]]):
                for p2 in range(kern[conn[1]]):
                    orig = conn[0] + str(p1)
                    dest = conn[1] + str(p2)
                    token_size = conn[2]
                    channel = DataflowChannel(orig + "_" + dest, token_size)
                    channels[orig + "_" + dest] = channel
                    kernels[orig].connect_to_outgoing_channel(channel)
                    kernels[dest].connect_to_incomming_channel(channel)

        # register all processes
        for k in kernels:
            self.add_process(kernels[k])

        # register all channels
        for c in channels:
            self.add_channel(channels[c])

    @staticmethod
    def from_hydra(id, prbs, modulation_scheme, layers, **kwargs):
        # a little hacky, but it does the trick to instantiate the graph
        # directly from hydra.
        class Object(object):
            pass

        ntrace = Object()
        ntrace.PRBs = prbs
        ntrace.modulation_scheme = modulation_scheme
        ntrace.layers = layers
        return FivegGraph(id, ntrace)

