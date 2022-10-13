# Copyright (C) 2021 TU Dresden
# Licensed under the ISC license (see LICENSE.txt)
#
# Authors: Julian Robledo, Christian Menard

import hydra

from mocasin.common.trace import (
    DataflowTrace,
    ComputeSegment,
    ReadTokenSegment,
    WriteTokenSegment,
)

from fivegsim.graph.phybench import Phybench
from fivegsim.util.proc_tgff_reader import get_task_time


class FivegTrace(DataflowTrace):
    """Generates traces for the 5G application."""

    class KernelTrace:
        """Represents a single LTE trace."""

        def __init__(
            self,
            name,
            n_firings,
            read_from,
            input_tokens,
            input_fully_interconnect,
            write_to,
            output_tokens,
            output_fully_interconnect,
            n_instances,
            processor_cycles,
        ):
            self.name = name
            self.n_firings = n_firings
            self.read_from = read_from
            self.input_tokens = input_tokens
            self.input_fully_interconnect = input_fully_interconnect
            self.write_to = write_to
            self.output_tokens = output_tokens
            self.output_fully_interconnect = output_fully_interconnect
            self.n_instances = n_instances
            self.processor_cycles = processor_cycles

    def __init__(self, ntrace, proc_time, antennas):

        # Number of tasks of each type
        num_ph1 = Phybench.get_num_micf(ntrace.layers, antennas)
        num_ph2 = Phybench.get_num_combwc()
        num_ph3 = Phybench.get_num_antcomb(ntrace.layers)
        num_ph4 = Phybench.get_num_demap()

        prbs = ntrace.PRBs
        mod = ntrace.modulation_scheme
        if mod == 1:
            mod = 0
        elif mod == 2:
            mod = 1
        elif mod == 4:
            mod = 2
        elif mod == 6:
            mod = 3
        elif mod == 8:
            mod = 4

        # the following frequency settings were also used in the real odroid
        # platform to measure task execution time
        # here frequencies are hard-coded since a single platform can have
        # multiple frequency domains
        freq = {
            "ARM_CORTEX_A7": 1500000000,
            "ARM_CORTEX_A15": 1800000000,
            "acc": 250000000,
        }

        # calculate clock cycles for each task type
        armA7 = "ARM_CORTEX_A7"
        armA15 = "ARM_CORTEX_A15"
        fft_acc = "acc:fft,ifftm,iffta"

        pcs_input ={
            "ARM_CORTEX_A7": 0,
            "ARM_CORTEX_A15": 0,
        }
        pcs_mf = {
            armA7: proc_time["mf"][armA7][prbs] * freq[armA7],
            armA15: proc_time["mf"][armA15][prbs] * freq[armA15],
            "acc:mf": proc_time["mf"]["acc_mf"][prbs] * freq["acc"],
        }
        pcs_fft = {
            armA7: proc_time["fft"][armA7][prbs] * freq[armA7],
            armA15: proc_time["fft"][armA15][prbs] * freq[armA15],
            fft_acc: proc_time["fft"]["acc_fft"][prbs] * freq["acc"],
        }
        pcs_ifftm = {
            armA7: proc_time["fft"][armA7][prbs] * freq[armA7],
            armA15: proc_time["fft"][armA15][prbs] * freq[armA15],
            fft_acc: proc_time["fft"]["acc_fft"][prbs] * freq["acc"],
        }
        pcs_iffta = {
            armA7: proc_time["fft"][armA7][prbs] * freq[armA7],
            armA15: proc_time["fft"][armA15][prbs] * freq[armA15],
            fft_acc: proc_time["fft"]["acc_fft"][prbs] * freq["acc"],
        }
        pcs_wind = {
            armA7: proc_time["wind"][armA7][prbs] * freq[armA7],
            armA15: proc_time["wind"][armA15][prbs] * freq[armA15],
            "acc:wind": proc_time["wind"]["acc_wind"][prbs] * freq["acc"],
        }
        pcs_comb = {
            armA7: proc_time["comb"][armA7][prbs] * freq[armA7] * (ntrace.layers / 4),
            armA15: proc_time["comb"][armA15][prbs] * freq[armA15] * (ntrace.layers / 4),
            "acc:comb": proc_time["comb"]["acc_comb"][prbs] * freq["acc"] * (ntrace.layers / 4) / 12,
        }
        pcs_ant = {
            armA7: proc_time["ant"][armA7][prbs] * freq[armA7],
            armA15: proc_time["ant"][armA15][prbs] * freq[armA15],
            "acc:ant": proc_time["ant"]["acc_ant"][prbs] * freq["acc"],
        }
        pcs_demap = {
            armA7: proc_time["demap"][armA7][mod][prbs] * freq[armA7] * (ntrace.layers / 4),
            armA15: proc_time["demap"][armA15][mod][prbs] * freq[armA15] * (ntrace.layers / 4),
            f"acc:demap{ntrace.modulation_scheme}": proc_time["demap"]["acc_demap"][mod][prbs] * freq["acc"] * (ntrace.layers / 4),
        }

        # kernels
        #
        # disable auto-formatting:
        # fmt: off
        self.processes = {
            "input": self.KernelTrace(
                "input", 2,
                [], [None], [False],
                ["mf", "ant"], [1, 1], [True, True],
                1, pcs_input,
            ),
            "mf": self.KernelTrace(
                "mf", 2,
                ["input"], [1], [True],
                ["ifftm"], [1], [False],
                num_ph1, pcs_mf,
            ),
            "ifftm": self.KernelTrace(
                "ifftm", 2,
                ["mf"], [1], [False],
                ["wind"], [1], [False],
                num_ph1, pcs_ifftm,
            ),
            "wind": self.KernelTrace(
                "wind", 2,
                ["ifftm"], [1], [False],
                ["fft"], [1], [False],
                num_ph1, pcs_wind,
            ),
            "fft": self.KernelTrace(
                "fft", 2,
                ["wind"], [1], [False],
                ["comb"], [1], [True],
                num_ph1, pcs_fft,
            ),
            "comb": self.KernelTrace(
                "comb", 2,
                ["fft"], [1], [True],
                ["ant"], [1], [True],
                num_ph2, pcs_comb,
            ),
            "ant": self.KernelTrace(
                "ant", 2,
                ["input", "comb"], [1, 1], [True, True],
                ["iffta"], [1], [False],
                num_ph3, pcs_ant,
            ),
            "iffta": self.KernelTrace(
                "iffta", 2,
                ["ant"], [1], [False],
                [f"demap{mod}"], [1], [True],
                num_ph3, pcs_iffta,
            ),
            f"demap{mod}": self.KernelTrace(
                f"demap{mod}", 1,
                ["iffta"], [2], [True],
                ["output"], [1], [True],
                num_ph4, pcs_demap,
            ),
            "output": self.KernelTrace(
                "output", 1,
                [f"demap{mod}"], [1], [True],
                [], [None], [False],
                1, pcs_input,
            ),
        }
        # enabling autoformatting back
        # fmt: on

    def get_trace(self, process):
        kern = next(
            val
            for key, val in self.processes.items()
            if process.startswith(key)
        )
        if not kern:
            raise RuntimeError(f"Unknown process {process}")

        for firing in range(kern.n_firings):
            # read tokens from input channels
            for i in range(len(kern.read_from)):
                orig_name = kern.read_from[i]
                orig = next(
                    val
                    for key, val in self.processes.items()
                    if key.startswith(orig_name)
                )
                if kern.input_fully_interconnect[i]:
                    for n in range(orig.n_instances):
                        yield ReadTokenSegment(
                            channel=f"{orig_name}{n}_{process}",
                            num_tokens=kern.input_tokens[i],
                        )
                else:
                    n = process.replace(kern.name, "")
                    yield ReadTokenSegment(
                        channel=f"{orig_name}{n}_{process}",
                        num_tokens=kern.input_tokens[i],
                    )

            # Process tasks
            yield ComputeSegment(kern.processor_cycles)

            # write tokens to ouput channels
            for i in range(len(kern.write_to)):
                dest_name = kern.write_to[i]
                dest = next(
                    val
                    for key, val in self.processes.items()
                    if key.startswith(dest_name)
                )
                if kern.output_fully_interconnect[i]:
                    for n in range(dest.n_instances):
                        yield WriteTokenSegment(
                            channel=f"{process}_{dest_name}{n}",
                            num_tokens=kern.output_tokens[i],
                        )
                else:
                    n = process.replace(kern.name, "")
                    yield WriteTokenSegment(
                        channel=f"{process}_{dest_name}{n}",
                        num_tokens=kern.output_tokens[i],
                    )

    @staticmethod
    def from_hydra(task_file, prbs, modulation_scheme, layers, antennas, **kwargs):
        # a little hacky, but it does the trick to instantiate the graph
        # directly from hydra.
        class Object(object):
            pass

        ntrace = Object()
        ntrace.PRBs = prbs
        ntrace.modulation_scheme = modulation_scheme
        ntrace.layers = layers

        proc_time = get_task_time(hydra.utils.to_absolute_path(task_file))

        return FivegTrace(ntrace, proc_time, antennas)
