# Copyright (C) 2021 TU Dresden
# All Rights Reserved
#
# Authors: Julian Robledo, Christian Menard

import hydra

from mocasin.common.trace import (
    DataflowTrace,
    ComputeSegment,
    ReadTokenSegment,
    WriteTokenSegment
)

from fivegsim.phybench import PHY
from fivegsim.proc_tgff_reader import get_task_time

class FivegTrace(DataflowTrace):
    """Generates traces for the 5G application"""

    class kernelTrace:
        """Represents a single LTE trace."""

        def __init__(self, name, n_firings, read_from, input_tokens,
                     write_to, output_tokens, n_instances,
                     processor_cycles):
            self.name = name
            self.n_firings = n_firings
            self.read_from = read_from
            self.input_tokens = input_tokens
            self.write_to = write_to
            self.output_tokens = output_tokens
            self.n_instances = n_instances
            self.processor_cycles = processor_cycles

    def __init__(self, ntrace, proc_time):

        # Number of tasks of each type
        num_ph1 = PHY.get_num_micf(ntrace.layers)
        num_ph2 = PHY.get_num_combwc()
        num_ph3 = PHY.get_num_antcomb(ntrace.layers)
        num_ph4 = PHY.get_num_demap()

        prbs = ntrace.PRBs
        mod = ntrace.modulation_scheme

        # kernel names
        kernels = ["input",
                   "mf",
                   "ifft1",
                   "wind",
                   "fft",
                   "comb",
                   "ant",
                   "ifft2",
                   "demap",
                   "output"]

        # number of firings for each kernel type
        firings = [2, 2, 2, 2, 2, 2, 2, 2, 1, 1]

        # processes read from
        read_from = [[],
                     ["input"], 
                     ["mf"],
                     ["ifft1"], 
                     ["wind"],
                     ["fft"],
                     ["input","comb"],
                     ["ant"],
                     ["ifft2"],
                     ["demap"]]

        # number of input tokens
        input_tokens = [[None], [1], [1], [1], [1], [1], [1,1], [1], [2], [1]]

        # processes read from
        write_to = [["mf", "ant"],
                    ["ifft1"],
                    ["wind"],
                    ["fft"],
                    ["comb"],
                    ["ant"],
                    ["ifft2"],
                    ["demap"],
                    ["output"],
                    []]

        # number of input tokens
        output_tokens = [[1,1], [1], [1], [1], [1], [1], [1], [1], [1], [None]]

        # number of instances for each kernel
        n_instances = [1,
                          num_ph1,
                          num_ph1,
                          num_ph1,
                          num_ph1,
                          num_ph2,
                          num_ph3,
                          num_ph3,
                          num_ph4,
                          1]

        # offsets on tgff file
        offset = [None,
                  prbs - 1,
                  prbs + 100 - 1,
                  prbs + 200 - 1, 
                  prbs + 100 - 1,
                  prbs + 300 - 1,
                  prbs + 400 - 1,
                  prbs + 100 - 1,
                  prbs + (500 + 100 * mod) - 1,
                  None]

        # processors and frequency
        freq = {
            "ARM_CORTEX_A7" : 1300000000, # ARM_CORTEX_A7
            "ARM_CORTEX_A15" : 2000000000  # ARM_CORTEX_A15
        }

        pcs = {}
        pcs["input"] = {"ARM_CORTEX_A7" : 0, "ARM_CORTEX_A15" : 0}
        pcs["output"] = {"ARM_CORTEX_A7" : 0, "ARM_CORTEX_A15" : 0}
        for k in range(len(kernels)):
            if (kernels[k] != "input") & (kernels[k] != "output"):
                pcs[kernels[k]] = {
                    "ARM_CORTEX_A7" : proc_time[0][offset[k]] * freq["ARM_CORTEX_A7"],
                    "ARM_CORTEX_A15" : proc_time[1][offset[k]] * freq["ARM_CORTEX_A15"]
                }

        self.processes = {}
        for k in range(len(kernels)):
            self.processes[kernels[k]] =  self.kernelTrace(
                                        kernels[k],
                                        firings[k],
                                        read_from[k],
                                        input_tokens[k],
                                        write_to[k],
                                        output_tokens[k],
                                        n_instances[k],
                                        pcs[kernels[k]]
            )

    def get_trace(self, process):
        yield from self._generic_trace(process)

    def _generic_trace(self, process):
        kern = next(val for key, val in self.processes.items() if process.startswith(key))
        #else:
            #raise RuntimeError(f"Unknown process {process}")
        for firing in range(kern.n_firings):
            # read tokens from input
            for i in range(len(kern.read_from)):
                orig_name = kern.read_from[i]
                orig = next(val for key, 
                             val in self.processes.items() if key.startswith(orig_name))
                for n in range(orig.n_instances):
                    yield ReadTokenSegment(
                        channel=f"{orig_name}{n}_{process}",
                        num_tokens=kern.input_tokens[i]
                    )

            # Process tasks
            yield ComputeSegment(kern.processor_cycles)

            # write tokens to ouput
            for i in range(len(kern.write_to)):
                dest_name = kern.write_to[i]
                dest = next(val for key,
                             val in self.processes.items() if key.startswith(dest_name))
                for n in range(dest.n_instances):
                    yield WriteTokenSegment(
                        channel=f"{process}_{dest_name}{n}",
                        num_tokens=kern.output_tokens[i]
                    )

    @staticmethod
    def from_hydra(task_file, prbs, modulation_scheme, layers, **kwargs):
        # a little hacky, but it does the trick to instantiate the graph
        # directly from hydra.
        class Object(object):
            pass

        ntrace = Object()
        ntrace.PRBs = prbs
        ntrace.modulation_scheme = modulation_scheme
        ntrace.layers = layers

        proc_time = get_task_time(hydra.utils.to_absolute_path(task_file))

        return FivegTrace(ntrace, proc_time)