# Copyright (C) 2021 TU Dresden
# All Rights Reserved
#
# Authors: Julian Robledo, Christian Menard

from mocasin.common.graph import DataflowGraph, DataflowProcess, DataflowChannel
from fivegsim.phybench import Phybench


class FivegGraph(DataflowGraph):
    """The Dataflow graph of a 5G application

    The 5G application has the following type of tasks:
    micf, combwc, antcomb, demap.
    """

    def __init__(self, name, ntrace):
        super().__init__(name)

        self.prbs = ntrace.PRBs
        self.mod = ntrace.modulation_scheme
        self.criticality = ntrace.UE_criticality

        prbs = ntrace.PRBs
        mod = ntrace.modulation_scheme
        lay = ntrace.layers
        ant = Phybench.num_antenna
        sc = Phybench.SC
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

        num_phase1 = Phybench.get_num_micf(lay)
        num_phase2 = Phybench.get_num_combwc()
        num_phase3 = Phybench.get_num_antcomb(lay)
        num_phase4 = Phybench.get_num_demap()

        # kernels: name, number of instances
        kernels = {
            "input": {"num_instances": 1, "subkernels": ["input"]},
            "phase1": {
                "num_instances": num_phase1,
                "subkernels": ["mf", "ifftm", "wind", "fft"],
            },
            "phase2": {"num_instances": num_phase2, "subkernels": ["comb"]},
            "phase3": {
                "num_instances": num_phase3,
                "subkernels": ["ant", "iffta"],
            },
            "phase4": {"num_instances": num_phase4, "subkernels": ["demap"]},
            "output": {"num_instances": 1, "subkernels": ["output"]},
        }

        # connections: origin, destination, token size
        kernel_connections = [
            ["input", "phase1", data_size * nmbSc],
            ["input", "phase3", data_size * nmbSc * ant],
            ["phase1", "phase2", data_size * prbs],
            ["phase2", "phase3", data_size * prbs * ant],
            ["phase3", "phase4", (data_size * prbs) / 2],
            ["phase4", "output", data_size * prbs * mod],
        ]

        # connections: phase, origin, destination, token size
        subkernel_connections = [
            ["phase1", "mf", "ifftm", data_size * nmbSc],
            ["phase1", "ifftm", "wind", data_size * nmbSc],
            ["phase1", "wind", "fft", data_size * nmbSc],
            ["phase3", "ant", "iffta", data_size * prbs],
        ]

        # add processes
        processes = {}
        for k in kernels:
            for s in kernels[k]["subkernels"]:
                for n in range(kernels[k]["num_instances"]):
                    process_name = s + str(n)
                    processes[process_name] = DataflowProcess(process_name)

        channels = {}

        # Fully interconnect phases
        for conn in kernel_connections:
            for p1 in range(kernels[conn[0]]["num_instances"]):
                for p2 in range(kernels[conn[1]]["num_instances"]):
                    orig = kernels[conn[0]]["subkernels"][-1] + str(p1)
                    dest = kernels[conn[1]]["subkernels"][0] + str(p2)
                    token_size = conn[2]
                    channel = DataflowChannel(orig + "_" + dest, token_size)
                    channels[orig + "_" + dest] = channel
                    processes[orig].connect_to_outgoing_channel(channel)
                    processes[dest].connect_to_incomming_channel(channel)

        # interconnect subkernels inside a kernel
        for conn in subkernel_connections:
            for p1 in range(kernels[conn[0]]["num_instances"]):
                orig = conn[1] + str(p1)
                dest = conn[2] + str(p1)
                token_size = conn[3]
                channel = DataflowChannel(orig + "_" + dest, token_size)
                channels[orig + "_" + dest] = channel
                processes[orig].connect_to_outgoing_channel(channel)
                processes[dest].connect_to_incomming_channel(channel)

        # register all processes
        for p in processes:
            self.add_process(processes[p])

        # register all channels
        for c in channels:
            self.add_channel(channels[c])

    @property
    def timeout(self):
        if self.criticality == 0:
            timeout = 2500000000
        elif self.criticality == 1:
            timeout = 500000000
        elif self.criticality == 2:
            timeout = 2500000000
        else:
            raise ValueError("Unknown criticality")
        return timeout

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
        ntrace.UE_criticality = None
        return FivegGraph(f"fiveg{id}", ntrace)
