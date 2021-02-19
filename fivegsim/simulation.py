import copy
import logging
import hydra
import sys

from mocasin.common.graph import DataflowGraph, DataflowProcess, DataflowChannel
from mocasin.common.mapping import Mapping
from mocasin.common.trace import (
    DataflowTrace,
    ComputeSegment,
    ReadTokenSegment,
    WriteTokenSegment,
    SegmentType,
)
from mocasin.simulate import BaseSimulation
from mocasin.simulate.application import RuntimeDataflowApplication

from fivegsim.trace_file_manager import TraceFileManager
from fivegsim.phybench import PHY
from fivegsim.phybench import LTE
from fivegsim.proc_tgff_reader import get_task_time


sys.setrecursionlimit(10000)

log = logging.getLogger(__name__)


class FivegGraph(DataflowGraph):
    """The Dataflow graph of a 5G application

    The 5G application has the following type of tasks:
    micf, combwc, antcomb, demap.
    """

    def __init__(self, i, ntrace):
        super().__init__(f"fiveg{i}")

        # Number of processes for each phase
        self.num_ph1 = PHY.get_num_micf(ntrace.layers)
        self.num_ph2 = PHY.get_num_combwc()
        self.num_ph3 = PHY.get_num_antcomb(ntrace.layers)
        self.num_ph4 = PHY.get_num_demap()

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

        # dictionary for processes
        pin = {}  # input
        pmf = {}  # MatchedFilter
        pifft1 = {}  # IFFT1
        pwind = {}  # Windowing
        pfft = {}  # FFT
        pcomb = {}  # CombinerWeights
        pant = {}  # AntennaCombining
        pifft2 = {}  # IFFT2
        pdemap = {}  # Demap
        pout = {}  # output

        # dictionary for channels
        in_2_mf = {}  # input to MatchedFilter
        in_2_ac = {}  # input to AntennaCombining
        mf_2_if = {}  # MatchedFilter to IFFT
        if_2_wd = {}  # IFFT to Windowing
        wd_2_ff = {}  # Windowing to FFT
        ff_2_cw = {}  # FFT to CombinerWeights
        cw_2_ac = {}  # CombinerWeights to AntennaCombining
        ac_2_if = {}  # AntennaCombining to IFFT
        if_2_dm = {}  # IFFT to Demap
        dm_2_out = {}  # Demap to Output

        # add processes to dictionaries
        process = "input"
        pin[process] = DataflowProcess(process)
        for ph1 in range(self.num_ph1):
            process = "mf" + str(ph1)
            pmf[process] = DataflowProcess(process)
            process = "ifft1" + str(ph1)
            pifft1[process] = DataflowProcess(process)
            process = "wind" + str(ph1)
            pwind[process] = DataflowProcess(process)
            process = "fft" + str(ph1)
            pfft[process] = DataflowProcess(process)
        for ph2 in range(self.num_ph2):
            process = "comb" + str(ph2)
            pcomb[process] = DataflowProcess(process)
        for ph3 in range(self.num_ph3):
            process = "ant" + str(ph3)
            pant[process] = DataflowProcess(process)
            process = "ifft2" + str(ph3)
            pifft2[process] = DataflowProcess(process)
        for ph4 in range(self.num_ph4):
            process = "demap" + str(ph4)
            pdemap[process] = DataflowProcess(process)
        process = "output"
        pout[process] = DataflowProcess(process)

        # add channels to dictionaries and connect processes
        # input to MatchedFilter
        for mf in range(self.num_ph1):
            orig = "input"
            dest = "mf" + str(mf)
            token_size = data_size * (nmbSc)
            channel = DataflowChannel(orig + "_" + dest, token_size)
            in_2_mf[orig + "_" + dest] = channel
            pin[orig].connect_to_outgoing_channel(channel)
            pmf[dest].connect_to_incomming_channel(channel)
        # input to AntennaCombining
        for ant in range(self.num_ph3):
            orig = "input"
            dest = "ant" + str(ant)
            token_size = data_size * (nmbSc * lay)
            channel = DataflowChannel(orig + "_" + dest, token_size)
            in_2_ac[orig + "_" + dest] = channel
            pin[orig].connect_to_outgoing_channel(channel)
            pant[dest].connect_to_incomming_channel(channel)
        # MatchedFilter to IFFT
        for mf in range(self.num_ph1):
            for ifft1 in range(self.num_ph1):
                orig = "mf" + str(mf)
                dest = "ifft1" + str(ifft1)
                token_size = data_size * nmbSc
                channel = DataflowChannel(orig + "_" + dest, token_size)
                mf_2_if[orig + "_" + dest] = channel
                pmf[orig].connect_to_outgoing_channel(channel)
                pifft1[dest].connect_to_incomming_channel(channel)
        # IFFT to Windowing
        for ifft1 in range(self.num_ph1):
            for wind in range(self.num_ph1):
                orig = "ifft1" + str(ifft1)
                dest = "wind" + str(wind)
                token_size = data_size * nmbSc
                channel = DataflowChannel(orig + "_" + dest, token_size)
                if_2_wd[orig + "_" + dest] = channel
                pifft1[orig].connect_to_outgoing_channel(channel)
                pwind[dest].connect_to_incomming_channel(channel)
        # Windowing to FFT
        for wind in range(self.num_ph1):
            for fft in range(self.num_ph1):
                orig = "wind" + str(wind)
                dest = "fft" + str(fft)
                token_size = data_size * nmbSc
                channel = DataflowChannel(orig + "_" + dest, token_size)
                wd_2_ff[orig + "_" + dest] = channel
                pwind[orig].connect_to_outgoing_channel(channel)
                pfft[dest].connect_to_incomming_channel(channel)
        # FFT to CombinerWeights
        for fft in range(self.num_ph1):
            for comb in range(self.num_ph2):
                orig = "fft" + str(fft)
                dest = "comb" + str(comb)
                token_size = data_size * nmbSc
                channel = DataflowChannel(orig + "_" + dest, token_size)
                ff_2_cw[orig + "_" + dest] = channel
                pfft[orig].connect_to_outgoing_channel(channel)
                pcomb[dest].connect_to_incomming_channel(channel)
        # CombinerWeights to AntennaCombining
        for comb in range(self.num_ph2):
            for ant in range(self.num_ph3):
                orig = "comb" + str(comb)
                dest = "ant" + str(ant)
                token_size = data_size * prbs * ant
                channel = DataflowChannel(orig + "_" + dest, token_size)
                cw_2_ac[orig + "_" + dest] = channel
                pcomb[orig].connect_to_outgoing_channel(channel)
                pant[dest].connect_to_incomming_channel(channel)
        # AntennaCombining to IFFT
        for ant in range(self.num_ph3):
            for ifft2 in range(self.num_ph3):
                orig = "ant" + str(ant)
                dest = "ifft2" + str(ifft2)
                token_size = data_size * prbs * ant
                channel = DataflowChannel(orig + "_" + dest, token_size)
                ac_2_if[orig + "_" + dest] = channel
                pant[orig].connect_to_outgoing_channel(channel)
                pifft2[dest].connect_to_incomming_channel(channel)
        # IFFT to Demap
        for ifft2 in range(self.num_ph3):
            for demap in range(self.num_ph4):
                orig = "ifft2" + str(ifft2)
                dest = "demap" + str(demap)
                token_size = data_size * prbs
                channel = DataflowChannel(orig + "_" + dest, token_size)
                if_2_dm[orig + "_" + dest] = channel
                pifft2[orig].connect_to_outgoing_channel(channel)
                pdemap[dest].connect_to_incomming_channel(channel)
        # Demap to Output
        for demap in range(self.num_ph4):
            orig = "demap" + str(demap)
            dest = "output"
            token_size = data_size * prbs * mod
            channel = DataflowChannel(orig + "_" + dest, token_size)
            dm_2_out[orig + "_" + dest] = channel
            pdemap[orig].connect_to_outgoing_channel(channel)
            pout[dest].connect_to_incomming_channel(channel)

        # register all processes
        process = "input"
        self.add_process(pin[process])
        for ph1 in range(self.num_ph1):
            process = "mf" + str(ph1)
            self.add_process(pmf[process])
            process = "ifft1" + str(ph1)
            self.add_process(pifft1[process])
            process = "wind" + str(ph1)
            self.add_process(pwind[process])
            process = "fft" + str(ph1)
            self.add_process(pfft[process])
        for ph2 in range(self.num_ph2):
            process = "comb" + str(ph2)
            self.add_process(pcomb[process])
        for ph3 in range(self.num_ph3):
            process = "ant" + str(ph3)
            self.add_process(pant[process])
            process = "ifft2" + str(ph3)
            self.add_process(pifft2[process])
        for ph4 in range(self.num_ph4):
            process = "demap" + str(ph4)
            self.add_process(pdemap[process])
        process = "output"
        self.add_process(pout[process])

        # register all channels
        for mf in range(self.num_ph1):
            channel = "input" + "_" + "mf" + str(mf)
            self.add_channel(in_2_mf[channel])
        for ant in range(self.num_ph3):
            channel = "input" + "_" + "ant" + str(ant)
            self.add_channel(in_2_ac[channel])
        for mf in range(self.num_ph1):
            for ifft1 in range(self.num_ph1):
                channel = "mf" + str(mf) + "_" + "ifft1" + str(ifft1)
                self.add_channel(mf_2_if[channel])
        for ifft1 in range(self.num_ph1):
            for wind in range(self.num_ph1):
                channel = "ifft1" + str(ifft1) + "_" + "wind" + str(wind)
                self.add_channel(if_2_wd[channel])
        for wind in range(self.num_ph1):
            for fft in range(self.num_ph1):
                channel = "wind" + str(wind) + "_" + "fft" + str(fft)
                self.add_channel(wd_2_ff[channel])
        for fft in range(self.num_ph1):
            for comb in range(self.num_ph2):
                channel = "fft" + str(fft) + "_" + "comb" + str(comb)
                self.add_channel(ff_2_cw[channel])
        for comb in range(self.num_ph2):
            for ant in range(self.num_ph3):
                channel = "comb" + str(comb) + "_" + "ant" + str(ant)
                self.add_channel(cw_2_ac[channel])
        for ant in range(self.num_ph3):
            for ifft2 in range(self.num_ph3):
                channel = "ant" + str(ant) + "_" + "ifft2" + str(ifft2)
                self.add_channel(ac_2_if[channel])
        for ifft2 in range(self.num_ph3):
            for demap in range(self.num_ph4):
                channel = "ifft2" + str(ifft2) + "_" + "demap" + str(demap)
                self.add_channel(if_2_dm[channel])
        for demap in range(self.num_ph4):
            channel = "demap" + str(demap) + "_" + "output"
            self.add_channel(dm_2_out[channel])

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


class FivegTrace(DataflowTrace):
    """Generates traces for the 5G application"""

    def __init__(self, ntrace, proc_time):
        # build a dictionary of all the traces
        trace = {}

        # Number of tasks of each type
        self.num_ph1 = PHY.get_num_micf(ntrace.layers)
        self.num_ph2 = PHY.get_num_combwc()
        self.num_ph3 = PHY.get_num_antcomb(ntrace.layers)
        self.num_ph4 = PHY.get_num_demap()

        # number of PRBs
        prbs = ntrace.PRBs
        # modulation scheme
        mod = ntrace.modulation_scheme

        # clock frequency for core types Cortex A7 and Cortex15
        freq_cortex_a7 = 1300000000
        freq_cortex_a15 = 2000000000

        mf_offset = prbs - 1
        fft_offset = prbs + 100 - 1
        wind_offset = prbs + 200 - 1
        comb_offset = prbs + 300 - 1
        ant_offset = prbs + 400 - 1
        demap_offset = prbs + (500 + 100 * mod) - 1

        # process cycles for each task type on ARM_CORTEX_A7
        pc_mf_A7 = proc_time[0][mf_offset] * freq_cortex_a7
        pc_fft_A7 = proc_time[0][fft_offset] * freq_cortex_a7
        pc_ifft1_A7 = pc_fft_A7
        pc_ifft2_A7 = pc_fft_A7
        pc_wind_A7 = proc_time[0][wind_offset] * freq_cortex_a7
        pc_comb_A7 = proc_time[0][comb_offset] * freq_cortex_a7
        pc_ant_A7 = proc_time[0][ant_offset] * freq_cortex_a7
        pc_demap_A7 = proc_time[0][demap_offset] * freq_cortex_a7

        # process cycles for each task type on ARM_CORTEX_A15
        # FIXME: the calculated times below appear to be wrong
        pc_mf_A15 = proc_time[0][mf_offset] * freq_cortex_a15
        pc_fft_A15 = proc_time[0][fft_offset] * freq_cortex_a15
        pc_ifft1_A15 = pc_fft_A15
        pc_ifft2_A15 = pc_fft_A15
        pc_wind_A15 = proc_time[0][wind_offset] * freq_cortex_a15
        pc_comb_A15 = proc_time[0][comb_offset] * freq_cortex_a15
        pc_ant_A15 = proc_time[0][ant_offset] * freq_cortex_a15
        pc_demap_A15 = proc_time[0][demap_offset] * freq_cortex_a15

        self.mf_processor_cycles = {
            "ARM_CORTEX_A7": pc_mf_A7,
            "ARM_CORTEX_A15": pc_mf_A15,
        }
        self.fft_processor_cycles = {
            "ARM_CORTEX_A7": pc_fft_A7,
            "ARM_CORTEX_A15": pc_fft_A15,
        }
        self.ifft1_processor_cycles = {
            "ARM_CORTEX_A7": pc_ifft1_A7,
            "ARM_CORTEX_A15": pc_ifft1_A15,
        }
        self.ifft2_processor_cycles = {
            "ARM_CORTEX_A7": pc_ifft2_A7,
            "ARM_CORTEX_A15": pc_ifft2_A15,
        }
        self.wind_processor_cycles = {
            "ARM_CORTEX_A7": pc_wind_A7,
            "ARM_CORTEX_A15": pc_wind_A15,
        }
        self.comb_processor_cycles = {
            "ARM_CORTEX_A7": pc_comb_A7,
            "ARM_CORTEX_A15": pc_comb_A15,
        }
        self.ant_processor_cycles = {
            "ARM_CORTEX_A7": pc_ant_A7,
            "ARM_CORTEX_A15": pc_ant_A15,
        }
        self.demap_processor_cycles = {
            "ARM_CORTEX_A7": pc_demap_A7,
            "ARM_CORTEX_A15": pc_demap_A15,
        }

    def get_trace(self, process):
        if process == "input":
            yield from self._input_trace()
        elif process.startswith("mf"):
            yield from self._mf_trace(process)
        elif process.startswith("fft"):
            yield from self._fft_trace(process)
        elif process.startswith("ifft1"):
            yield from self._ifft1_trace(process)
        elif process.startswith("ifft2"):
            yield from self._ifft2_trace(process)
        elif process.startswith("wind"):
            yield from self._wind_trace(process)
        elif process.startswith("comb"):
            yield from self._comb_trace(process)
        elif process.startswith("ant"):
            yield from self._ant_trace(process)
        elif process.startswith("demap"):
            yield from self._demap_trace(process)
        elif process == "output":
            yield from self._output_trace()
        else:
            raise RuntimeError(f"Unknown process {process}")

    def _input_trace(self):
        # input task
        for slot in range(2):
            for mf in range(self.num_ph1):
                # write 1 token to MatchedFilter
                yield WriteTokenSegment(
                    channel="input_mf" + str(mf),
                    num_tokens=1,
                )
            for ant in range(self.num_ph3):
                # write 1 token to AntennaCombining
                yield WriteTokenSegment(
                    channel="input_ant" + str(ant),
                    num_tokens=1,
                )

    def _mf_trace(self, process):
        # MatchedFilter tasks
        for slot in range(2):
            # read 1 token from input
            yield ReadTokenSegment(channel=f"input_{process}", num_tokens=1)
            # Process tasks
            yield ComputeSegment(self.mf_processor_cycles)
            # write 1 token to IFFT1
            for ifft1 in range(self.num_ph1):
                yield WriteTokenSegment(
                    channel=f"{process}_ifft1{ifft1}", num_tokens=1
                )

    def _ifft1_trace(self, process):
        # IFFT1 tasks
        for slot in range(2):
            # read 1 token from MF
            for mf in range(self.num_ph1):
                yield ReadTokenSegment(
                    channel=f"mf{mf}_{process}", num_tokens=1
                )
            # Process tasks
            yield ComputeSegment(self.ifft1_processor_cycles)

            # write 1 token to Windowing
            for wind in range(self.num_ph1):
                yield WriteTokenSegment(
                    channel=f"{process}_wind{wind}", num_tokens=1
                )

    def _wind_trace(self, process):
        # Windowing tasks
        for slot in range(2):
            # read 1 token from IFFT1
            for ifft1 in range(self.num_ph1):
                yield ReadTokenSegment(
                    channel=f"ifft1{ifft1}_{process}", num_tokens=1
                )
            # Process tasks
            yield ComputeSegment(self.wind_processor_cycles)
            # write 1 token to FFT
            for fft in range(self.num_ph1):
                yield WriteTokenSegment(
                    channel=f"{process}_fft{fft}", num_tokens=1
                )

    def _fft_trace(self, process):
        # FFT tasks
        for slot in range(2):
            # read 1 token from IFFT1
            for wind in range(self.num_ph1):
                yield ReadTokenSegment(
                    channel=f"wind{wind}_{process}", num_tokens=1
                )
            # Process tasks
            yield ComputeSegment(self.fft_processor_cycles)
            # write 1 token to CombW
            for comb in range(self.num_ph2):
                yield WriteTokenSegment(
                    channel=f"{process}_comb{comb}", num_tokens=1
                )

    def _comb_trace(self, process):
        # CombW tasks
        for slot in range(2):
            # read 1 token from FFT
            for fft in range(self.num_ph1):
                yield ReadTokenSegment(
                    channel=f"fft{fft}_{process}", num_tokens=1
                )
            # Process tasks
            yield ComputeSegment(self.comb_processor_cycles)

            # write 1 token to AntComb
            for ant in range(self.num_ph3):
                yield WriteTokenSegment(
                    channel=f"{process}_ant{ant}", num_tokens=1
                )

    def _ant_trace(self, process):
        # AntComb tasks
        for slot in range(2):
            # read 1 token from input
            yield ReadTokenSegment(channel=f"input_{process}", num_tokens=1)
            # read 1 token from CombW
            for comb in range(self.num_ph2):
                yield ReadTokenSegment(
                    channel=f"comb{comb}_{process}", num_tokens=1
                )
            # Process tasks
            yield ComputeSegment(self.ant_processor_cycles)
            # write 1 token to IFFT2
            for ifft2 in range(self.num_ph3):
                yield WriteTokenSegment(
                    channel=f"{process}_ifft2{ifft2}", num_tokens=1
                )

    def _ifft2_trace(self, process):
        # IFFT2 tasks
        for slot in range(2):
            # read 1 token from AntComb
            for ant in range(self.num_ph3):
                yield ReadTokenSegment(
                    channel=f"ant{ant}_{process}", num_tokens=1
                )
            # Process tasks
            yield ComputeSegment(self.ifft2_processor_cycles)

            # write 1 token to Windowing
            for demap in range(self.num_ph4):
                yield WriteTokenSegment(
                    channel=f"{process}_demap{demap}", num_tokens=1
                )

    def _demap_trace(self, process):
        # Demap tasks
        # read 2 tokens from IFFT2
        for ifft2 in range(self.num_ph3):
            yield ReadTokenSegment(
                channel=f"ifft2{ifft2}_{process}", num_tokens=2
            )
        # Process tasks
        yield ComputeSegment(self.demap_processor_cycles)
        # write 1 token to output
        yield WriteTokenSegment(channel=f"{process}_output", num_tokens=1)

    def _output_trace(self):
        # Output task
        # read 1 token from Demap
        for demap in range(self.num_ph4):
            yield ReadTokenSegment(channel=f"demap{demap}_output", num_tokens=1)

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


class MergedFivegTrace(DataflowTrace):
    def __init__(self, prefixes, traces):
        self.prefixes = prefixes
        self.traces = {p: t for p, t in zip(prefixes, traces)}

    def get_trace(self, process):
        # find the prefix that matches the given process
        prefix = None
        for p in self.prefixes:
            if process.startswith(p):
                prefix = p
        assert prefix is not None

        process = process[len(prefix) :]  # remove the prefix from process name

        # iterate over all segments
        for segment in self.traces[prefix].get_trace(process):
            # add the prefix to all channel names
            if (
                segment.segment_type == SegmentType.WRITE_TOKEN
                or segment.segment_type == SegmentType.READ_TOKEN
            ):
                segment._channel = prefix + segment.channel

            yield segment


class FiveGSimulation(BaseSimulation):
    """Simulate the processing of 5G data"""

    def __init__(self, platform, cfg, trace_file, task_file, **kwargs):
        super().__init__(platform)
        self.cfg = cfg

        # Get lte traces
        self.TFM = TraceFileManager(hydra.utils.to_absolute_path(trace_file))
        self.ntrace = TraceFileManager.Trace()

        # Get task execution time info
        self.proc_time = get_task_time(hydra.utils.to_absolute_path(task_file))

    @staticmethod
    def from_hydra(cfg, **kwargs):
        platform = hydra.utils.instantiate(cfg["platform"])
        return FiveGSimulation(platform, cfg, **kwargs)

    def _manager_process(self):
        trace_writer = self.system.trace_writer

        app_finished = []
        criticalities = []
        prbs = []
        mod = []
        pStatFile = open("stats.csv", "w")
        pStatFile.write("startTime,endTime,criticality,miss,prbs,mod" + "\n")
        pStatFile.close()

        i = 0
        cnt = 0
        sf_count = 0
        # while end of file not reached:
        while self.TFM.TF_EOF is not True:

            nsubframe = self.TFM.get_next_subframe()
            sf_count += 1

            # run 100 instances of the 5G app, start one every 1 ms
            graphs = []
            traces = []
            for ntrace in nsubframe.trace:
                # create a new graph and trace
                self.ntrace = ntrace

                graphs.append(FivegGraph(i, self.ntrace))
                traces.append(FivegTrace(self.ntrace, self.proc_time))
                i += 1
                criticalities.append(ntrace.UE_criticality)
                prbs.append(ntrace.PRBs)
                mod.append(ntrace.modulation_scheme)

            # just wait and try again if there is nothing to process
            if len(graphs) == 0:
                # wait for 1 ms
                yield self.env.timeout(1000000000)
                continue

            # XXX Merge the applications and traces generated above into one
            # large graph and trace for the entire subframe. This is just a
            # workaround for our mapper API that only accepts a single mapping
            sf_graph = DataflowGraph(name=f"sf_{sf_count}")
            # work with a deepcopy of graphs so we don't need to be
            # afraid of breaking anything in the existing data structures and
            # can still use them later
            copy_graphs = copy.deepcopy(graphs)
            for graph in copy_graphs:
                # add all processes and channels to one large graph
                for p in graph.processes():
                    p.name = f"{graph.name}_{p.name}"
                    sf_graph.add_process(p)
                for c in graph.channels():
                    c.name = f"{graph.name}_{c.name}"
                    sf_graph.add_channel(c)

            # create a combined trace object
            prefixes = [f"{g.name}_" for g in copy_graphs]
            sf_trace = MergedFivegTrace(prefixes, traces)

            # create a new mapper (this should be TETRiS in the future) Note
            # that we need to create a new mapper here, as the GRAPH could change
            # This appears to be a weakness of our mapper interface. The GRAPH
            # should probably become a parameter of generate_mapping().
            log.info(f"generate mapping for {sf_graph.name}")
            rep = hydra.utils.instantiate(
                self.cfg["representation"], sf_graph, self.platform
            )
            mapper = hydra.utils.instantiate(
                self.cfg["mapper"], sf_graph, self.platform, sf_trace, rep
            )
            # create a mapping for the entire subframe
            sf_mapping = (
                mapper.generate_mapping()
            )  # TODO: collect and add load here
            log.info(f"mapping generation done")

            # split the mapping up again
            mappings = []
            for graph in graphs:
                mapping = Mapping(graph, self.platform)
                for sf_p in sf_mapping._process_info.keys():
                    if sf_p.startswith(graph.name):
                        p = sf_p[len(graph.name) + 1 :]
                        mapping._process_info[p] = sf_mapping._process_info[
                            sf_p
                        ]
                for sf_c in sf_mapping._channel_info.keys():
                    if sf_c.startswith(graph.name):
                        c = sf_c[len(graph.name) + 1 :]
                        mapping._channel_info[c] = sf_mapping._channel_info[
                            sf_c
                        ]
                mappings.append(mapping)

            log.info(f"start application {sf_graph.name}")
            # simulate the actual applications
            for mapping, trace in zip(mappings, traces):
                # instantiate the application
                app = FiveGRuntimeDataflowApplication(
                    name=mapping.graph.name,
                    graph=mapping.graph,
                    mapping=mapping,
                    app_trace=trace,
                    system=self.system,
                )
                # record application start in the simulation trace
                trace_writer.begin_duration("instances", app.name, app.name)
                # start the application
                finished = self.env.process(
                    app.run(criticalities[cnt], prbs[cnt], mod[cnt])
                )
                cnt += 1
                # register a callback to record the application termination
                # in the simulation trace
                finished.callbacks.append(
                    lambda _, name=app.name: trace_writer.end_duration(
                        "instances", name, name
                    )
                )
                # keep the finished event for later
                app_finished.append(finished)

            # wait for 1 ms
            yield self.env.timeout(1000000000)

        # wait until all applications finished
        yield self.env.all_of(app_finished)

        print("missrate = " + str(self.get_missrate()))

    def _run(self):
        """Run the simulation.

        May only be called once. Updates the :attr:`exec_time` attribute.
        """
        if self.exec_time is not None:
            raise RuntimeError("A FiveGSimulation may only be run once!")

        # start all schedulers
        self.system.start_schedulers()
        # start the manager process
        finished = self.env.process(self._manager_process())
        # run the actual simulation until the manager process finishes
        self.env.run(finished)
        # check if all graph processes finished execution
        self.system.check_errors()
        # save the execution time
        self.exec_time = self.env.now

    def get_missrate(self):
        pStatFile = open("stats.csv", "r")
        lines = pStatFile.readlines()  # Load all lines
        lines.pop(0)  # Remove first line
        lines = [x.strip() for x in lines]
        lines = [x.split(",") for x in lines]
        num_miss = 0
        for line in lines:
            num_miss += int(line[3])
        pStatFile.close()
        return num_miss / len(lines)


class FiveGRuntimeDataflowApplication(RuntimeDataflowApplication):
    def run(self, criticality, prbs, mod):
        """Start execution of this application

        Yields:
            ~simpy.events.Event: an event that is triggered when the
                application finishes execution.
        """
        miss = 0

        if criticality == 0:
            timeout = 2500000000
        elif criticality == 1:
            timeout = 500000000
        elif criticality == 2:
            timeout = 2500000000

        self._log.info(f"Application {self.name} starts")
        start = self.env.now
        for process, mapping_info in self._mapping_infos.items():
            self.system.start_process(process, mapping_info)
        finished = self.env.all_of([p.finished for p in self.processes()])
        finished.callbacks.append(
            lambda _: self._log.info(f"Application {self.name} terminates")
        )
        yield finished | self.env.timeout(timeout)
        end = self.env.now

        if not finished.processed:
            self.kill()
            miss = 1

        # save stats
        pStatFile = open("stats.csv", "a")
        pStatFile.write(
            str(start)
            + ","
            + str(end)
            + ","
            + str(criticality)
            + ","
            + str(miss)
            + ","
            + str(prbs)
            + ","
            + str(mod)
            + "\n"
        )
        pStatFile.close()
