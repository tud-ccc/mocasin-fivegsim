# Copyright (C) 2021 TU Dresden
# All Rights Reserved
#
# Authors: Julian Robledo, Christian Menard

import hydra

from mocasin.common.trace import (
    DataflowTrace,
    ComputeSegment,
    ReadTokenSegment,
    WriteTokenSegment,
)

from fivegsim.phybench import Phybench
from fivegsim.proc_tgff_reader import get_task_time


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

    def __init__(self, ntrace, proc_time):

        # Number of tasks of each type
        num_ph1 = Phybench.get_num_micf(ntrace.layers)
        num_ph2 = Phybench.get_num_combwc()
        num_ph3 = Phybench.get_num_antcomb(ntrace.layers)
        num_ph4 = Phybench.get_num_demap()

        prbs = ntrace.PRBs
        mod = ntrace.modulation_scheme

        # offsets on tgff file
        offset = [
            None,
            prbs - 1,
            prbs + 100 - 1,
            prbs + 200 - 1,
            prbs + 100 - 1,
            prbs + 300 - 1,
            prbs + 400 - 1,
            prbs + 100 - 1,
            prbs + (500 + 100 * mod) - 1,
            None,
        ]

        # clock cycles for FFT accelerator
        if prbs * 12 <= 8:
            fft_acc_cc = 94
        elif prbs * 12 <= 16:
            fft_acc_cc = 146
        elif prbs * 12 <= 32:
            fft_acc_cc = 242
        elif prbs * 12 <= 64:
            fft_acc_cc = 434
        elif prbs * 12 <= 128:
            fft_acc_cc = 834
        elif prbs * 12 <= 256:
            fft_acc_cc = 1682
        elif prbs * 12 <= 512:
            fft_acc_cc = 3490
        elif prbs * 12 <= 1024:
            fft_acc_cc = 7346
        elif prbs * 12 <= 2048:
            fft_acc_cc = 15554

        # the following frequency settings were also used in the real odroid
        # platform to measure task execution time
        # here frequencies are hard-coded since a single platform can have
        # multiple frequency domains
        freq = {
            "ARM_CORTEX_A7": 1500000000,
            "ARM_CORTEX_A15": 1800000000,
        }

        # calculate clock cycles for each task type
        pcs = []
        for k in range(len(offset)):
            if offset[k] is None:
                pcs.append(
                    {
                        "ARM_CORTEX_A7": 0,
                        "ARM_CORTEX_A15": 0,
                        "acc_fft,ifftm,iffta": 0,
                    }
                )
            else:
                pcs.append(
                    {
                        "ARM_CORTEX_A7": proc_time[0][offset[k]]
                        * freq["ARM_CORTEX_A7"],
                        "ARM_CORTEX_A15": proc_time[1][offset[k]]
                        * freq["ARM_CORTEX_A15"],
                        # FIXME: the accelerators cycle count is the A15 cycle
                        # count scaled down by factor 200. This is completely
                        # made up.
                        # Note that this scales down the cycle count for all
                        # kernels. However, we will only really use the fft ones
                        "acc_fft,ifftm,iffta": fft_acc_cc,
                    }
                )

        # kernels
        # fmt: off
        self.processes = {
            "input": self.KernelTrace(
                "input", 2,
                [], [None], [False],
                ["mf", "ant"], [1, 1], [True, True],
                1, pcs[0],
            ),
            "mf": self.KernelTrace(
                "mf", 2,
                ["input"], [1], [True],
                ["ifftm"], [1], [False],
                num_ph1, pcs[1],
            ),
            "ifftm": self.KernelTrace(
                "ifftm", 2,
                ["mf"], [1], [False],
                ["wind"], [1], [False],
                num_ph1, pcs[2],
            ),
            "wind": self.KernelTrace(
                "wind", 2,
                ["ifftm"], [1], [False],
                ["fft"], [1], [False],
                num_ph1, pcs[3],
            ),
            "fft": self.KernelTrace(
                "fft", 2,
                ["wind"], [1], [False],
                ["comb"], [1], [True],
                num_ph1, pcs[4],
            ),
            "comb": self.KernelTrace(
                "comb", 2,
                ["fft"], [1], [True],
                ["ant"], [1], [True],
                num_ph2, pcs[5],
            ),
            "ant": self.KernelTrace(
                "ant", 2,
                ["input", "comb"], [1, 1], [True, True],
                ["iffta"], [1], [False],
                num_ph3, pcs[6],
            ),
            "iffta": self.KernelTrace(
                "iffta", 2,
                ["ant"], [1], [False],
                ["demap"], [1], [True],
                num_ph3, pcs[7],
            ),
            "demap": self.KernelTrace(
                "demap", 1,
                ["iffta"], [2], [True],
                ["output"], [1], [True],
                num_ph4, pcs[8],
            ),
            "output": self.KernelTrace(
                "output", 1,
                ["demap"], [1], [True],
                [], [None], [False],
                1, pcs[9],
            ),
        }
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
