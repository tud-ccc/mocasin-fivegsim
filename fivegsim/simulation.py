import hydra

from pykpn.mapper.fair import StaticCFSMapperMultiApp
from pykpn.common.kpn import KpnGraph, KpnProcess, KpnChannel
from pykpn.common.trace import TraceGenerator, TraceSegment
from pykpn.simulate import BaseSimulation
from pykpn.simulate.application import RuntimeKpnApplication

from fivegsim.trace_file_manager import TraceFileManager
from fivegsim.phybench import PHY
from fivegsim.phybench import LTE
from fivegsim.proc_tgff_reader import get_task_time


class FivegGraph(KpnGraph):
    """The KPN graph of a 5G application
    
    The 5G application has the following type of tasks:
    micf, combwc, antcomb, demap.
    """

    def __init__(self,i,ntrace):
        super().__init__(f"fiveg{i}")

        # Number of processes for each phase
        self.num_ph1 = PHY.get_num_micf( ntrace.layers)
        self.num_ph2 = PHY.get_num_combwc()
        self.num_ph3 = PHY.get_num_antcomb(ntrace.layers)
        self.num_ph4 = PHY.get_num_demap()

        prbs = ntrace.PRBs
        mod = ntrace.modulation_scheme
        lay = ntrace.layers
        ant = LTE.num_antenna
        sc = LTE.SC
        data_size = 4 #bytes
        nmbSc = prbs*sc

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
        pin = {}    # input
        pmf = {}    # MatchedFilter
        pifft1 = {} # IFFT1
        pwind = {}  # Windowing
        pfft = {}   # FFT
        pcomb = {}  # CombinerWeights
        pant = {}   # AntennaCombining
        pifft2 = {} # IFFT2
        pdemap = {} # Demap
        pout = {}   # output

        # dictionary for channels
        in_2_mf = {}    # input to MatchedFilter
        in_2_ac = {}    # input to AntennaCombining
        mf_2_if = {}    # MatchedFilter to IFFT
        if_2_wd = {}    # IFFT to Windowing
        wd_2_ff = {}    # Windowing to FFT
        ff_2_cw = {}    # FFT to CombinerWeights
        cw_2_ac = {}    # CombinerWeights to AntennaCombining
        ac_2_if = {}    # AntennaCombining to IFFT
        if_2_dm = {}    # IFFT to Demap
        dm_2_out = {}   # Demap to Output

        # add processes to dictionaries
        process = "input"
        pin[process] = KpnProcess(process)
        for ph1 in range(self.num_ph1):
            process = "mf" + str(ph1)
            pmf[process] = KpnProcess(process)
            process = "ifft1" + str(ph1)
            pifft1[process] = KpnProcess(process)
            process = "wind" + str(ph1)
            pwind[process] = KpnProcess(process)
            process = "fft" + str(ph1)
            pfft[process] = KpnProcess(process)
        for ph2 in range(self.num_ph2):
            process = "comb" + str(ph2)
            pcomb[process] = KpnProcess(process)
        for ph3 in range(self.num_ph3):
            process = "ant" + str(ph3)
            pant[process] = KpnProcess(process)
            process = "ifft2" + str(ph3)
            pifft2[process] = KpnProcess(process)
        for ph4 in range(self.num_ph4):
            process = "demap" + str(ph4)
            pdemap[process] = KpnProcess(process)
        process = "output"
        pout[process] = KpnProcess(process)

        # add channels to dictionaries and connect processes
        # input to MatchedFilter
        for mf in range(self.num_ph1):
            orig = "input"
            dest = "mf" + str(mf)
            token_size = data_size*(nmbSc)
            channel = KpnChannel(orig + "_" + dest, token_size)
            in_2_mf[orig + "_" + dest] = channel
            pin[orig].connect_to_outgoing_channel(channel)
            pmf[dest].connect_to_incomming_channel(channel)
        # input to AntennaCombining
        for ant in range(self.num_ph3):
            orig = "input"
            dest = "ant" + str(ant)
            token_size = data_size*(nmbSc*lay)
            channel = KpnChannel(orig + "_" + dest, token_size)
            in_2_ac[orig + "_" + dest] = channel
            pin[orig].connect_to_outgoing_channel(channel)
            pant[dest].connect_to_incomming_channel(channel)
        # MatchedFilter to IFFT
        for mf in range(self.num_ph1):
            for ifft1 in range(self.num_ph1):
                orig = "mf" + str(mf)
                dest = "ifft1" + str(ifft1)
                token_size = data_size*nmbSc
                channel = KpnChannel(orig + "_" + dest, token_size)
                mf_2_if[orig + "_" + dest] = channel
                pmf[orig].connect_to_outgoing_channel(channel)
                pifft1[dest].connect_to_incomming_channel(channel)
        # IFFT to Windowing
        for ifft1 in range(self.num_ph1):
            for wind in range(self.num_ph1):
                orig = "ifft1" + str(ifft1)
                dest = "wind" + str(wind)
                token_size = data_size*nmbSc
                channel = KpnChannel(orig + "_" + dest, token_size)
                if_2_wd[orig + "_" + dest] = channel
                pifft1[orig].connect_to_outgoing_channel(channel)
                pwind[dest].connect_to_incomming_channel(channel)
        # Windowing to FFT
        for wind in range(self.num_ph1):
            for fft in range(self.num_ph1):
                orig = "wind" + str(wind)
                dest = "fft" + str(fft)
                token_size = data_size*nmbSc
                channel = KpnChannel(orig + "_" + dest, token_size)
                wd_2_ff[orig + "_" + dest] = channel
                pwind[orig].connect_to_outgoing_channel(channel)
                pfft[dest].connect_to_incomming_channel(channel)
        # FFT to CombinerWeights
        for fft in range(self.num_ph1):
            for comb in range(self.num_ph2):
                orig = "fft" + str(fft)
                dest = "comb" + str(comb)
                token_size = data_size*nmbSc
                channel = KpnChannel(orig + "_" + dest, token_size)
                ff_2_cw[orig + "_" + dest] = channel
                pfft[orig].connect_to_outgoing_channel(channel)
                pcomb[dest].connect_to_incomming_channel(channel)
        # CombinerWeights to AntennaCombining
        for comb in range(self.num_ph2):
            for ant in range(self.num_ph3):
                orig = "comb" + str(comb)
                dest = "ant" + str(ant)
                token_size = data_size*prbs*ant
                channel = KpnChannel(orig + "_" + dest, token_size)
                cw_2_ac[orig + "_" + dest] = channel
                pcomb[orig].connect_to_outgoing_channel(channel)
                pant[dest].connect_to_incomming_channel(channel)
        # AntennaCombining to IFFT
        for ant in range(self.num_ph3):
            for ifft2 in range(self.num_ph3):
                orig = "ant" + str(ant)
                dest = "ifft2" + str(ifft2)
                token_size = data_size*prbs*ant
                channel = KpnChannel(orig + "_" + dest, token_size)
                ac_2_if[orig + "_" + dest] = channel
                pant[orig].connect_to_outgoing_channel(channel)
                pifft2[dest].connect_to_incomming_channel(channel)
        # IFFT to Demap
        for ifft2 in range(self.num_ph3):
            for demap in range(self.num_ph4):
                orig = "ifft2" + str(ifft2)
                dest = "demap" + str(demap)
                token_size = data_size*prbs
                channel = KpnChannel(orig + "_" + dest, token_size)
                if_2_dm[orig + "_" + dest] = channel
                pifft2[orig].connect_to_outgoing_channel(channel)
                pdemap[dest].connect_to_incomming_channel(channel)
        # Demap to Output
        for demap in range(self.num_ph4):
            orig = "demap" + str(demap)
            dest = "output"
            token_size = data_size*prbs*mod
            channel = KpnChannel(orig + "_" + dest, token_size)
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

class FivegTraceGenerator(TraceGenerator):
    """Generates traces for the 5G application
    """

    def __init__(self, ntrace, proc_time):
        # build a dictionary of all the traces
        trace = {}

        # Number of tasks of each type
        self.num_ph1 = PHY.get_num_micf( ntrace.layers)
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

        mf_offset = prbs-1
        fft_offset = prbs+ 100 - 1
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
        pc_mf_A15 = proc_time[0][mf_offset] * freq_cortex_a15
        pc_fft_A15 = proc_time[0][fft_offset] * freq_cortex_a15
        pc_ifft1_A15 = pc_fft_A15
        pc_ifft2_A15 = pc_fft_A15
        pc_wind_A15 = proc_time[0][wind_offset] * freq_cortex_a15
        pc_comb_A15 = proc_time[0][comb_offset] * freq_cortex_a15
        pc_ant_A15 = proc_time[0][ant_offset] * freq_cortex_a15
        pc_demap_A15 = proc_time[0][demap_offset] * freq_cortex_a15

        # Define trace dictionaries
        trace["input"] = {}
        trace["input"]["ARM_CORTEX_A7"] = list()
        trace["input"]["ARM_CORTEX_A15"] = list()
        trace["output"] = {}
        trace["output"]["ARM_CORTEX_A7"] = list()
        trace["output"]["ARM_CORTEX_A15"] = list()
        for ph1 in range(self.num_ph1):
            trace["mf" + str(ph1)] = {}
            trace["mf" + str(ph1)]["ARM_CORTEX_A7"] = list()
            trace["mf" + str(ph1)]["ARM_CORTEX_A15"] = list()
            trace["ifft1" + str(ph1)] = {}
            trace["ifft1" + str(ph1)]["ARM_CORTEX_A7"] = list()
            trace["ifft1" + str(ph1)]["ARM_CORTEX_A15"] = list()
            trace["wind" + str(ph1)] = {}
            trace["wind" + str(ph1)]["ARM_CORTEX_A7"] = list()
            trace["wind" + str(ph1)]["ARM_CORTEX_A15"] = list()
            trace["fft" + str(ph1)] = {}
            trace["fft" + str(ph1)]["ARM_CORTEX_A7"] = list()
            trace["fft" + str(ph1)]["ARM_CORTEX_A15"] = list()
        for ph2 in range(self.num_ph2):
            trace["comb" + str(ph2)] = {}
            trace["comb" + str(ph2)]["ARM_CORTEX_A7"] = list()
            trace["comb" + str(ph2)]["ARM_CORTEX_A15"] = list()
        for ph3 in range(self.num_ph3):
            trace["ant" + str(ph3)] = {}
            trace["ant" + str(ph3)]["ARM_CORTEX_A7"] = list()
            trace["ant" + str(ph3)]["ARM_CORTEX_A15"] = list()
            trace["ifft2" + str(ph3)] = {}
            trace["ifft2" + str(ph3)]["ARM_CORTEX_A7"] = list()
            trace["ifft2" + str(ph3)]["ARM_CORTEX_A15"] = list()
        for ph4 in range(self.num_ph4):
            trace["demap" + str(ph4)] = {}
            trace["demap" + str(ph4)]["ARM_CORTEX_A7"] = list()
            trace["demap" + str(ph4)]["ARM_CORTEX_A15"] = list()

        for slot in range(2):
            # input task
            for mf in range(self.num_ph1):
                # write 1 token to MatchedFilter
                trace["input"]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles=0,
                write_to_channel="input" + "_" + "mf" + str(mf),
                n_tokens=1))
                trace["input"]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles=0,
                write_to_channel="input" + "_" + "mf" + str(mf),
                n_tokens=1))

            for ant in range(self.num_ph3):
                # write 1 token to AntennaCombining
                trace["input"]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles=0,
                write_to_channel="input" + "_" + "ant" + str(ant),
                n_tokens=1))
                trace["input"]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles=0,
                write_to_channel="input" + "_" + "ant" + str(ant),
                n_tokens=1))

            # MatchedFilter tasks
            for mf in range(self.num_ph1):
                # read 1 token from input
                trace["mf" + str(mf)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles=0,
                read_from_channel="input" + "_" + "mf" + str(mf),
                n_tokens=1))
                trace["mf" + str(mf)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles=0,
                read_from_channel="input" + "_" + "mf" + str(mf),
                n_tokens=1))

                # Process tasks
                trace["mf" + str(mf)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles = pc_mf_A7))
                trace["mf" + str(mf)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles = pc_mf_A15))

                # write 1 token to IFFT1
                for ifft1 in range(self.num_ph1):
                    trace["mf" + str(mf)]["ARM_CORTEX_A7"].\
                    append(TraceSegment(process_cycles=0,
                    write_to_channel="mf" + str(mf) + "_" + "ifft1" + str(ifft1),
                    n_tokens=1))
                    trace["mf" + str(mf)]["ARM_CORTEX_A15"].\
                    append(TraceSegment(process_cycles=0,
                    write_to_channel="mf" + str(mf) + "_" + "ifft1" + str(ifft1),
                    n_tokens=1))

            # IFFT1 tasks
            for ifft1 in range(self.num_ph1):
                # read 1 token from MF
                for mf in range(self.num_ph1):
                    trace["ifft1" + str(ifft1)]["ARM_CORTEX_A7"].\
                    append(TraceSegment(process_cycles=0,
                    read_from_channel="mf" + str(mf) + "_" + "ifft1" + str(ifft1),
                    n_tokens=1))
                    trace["ifft1" + str(ifft1)]["ARM_CORTEX_A15"].\
                    append(TraceSegment(process_cycles=0,
                    read_from_channel="mf" + str(mf) + "_" + "ifft1" + str(ifft1),
                    n_tokens=1))

                # Process tasks
                trace["ifft1" + str(ifft1)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles = pc_ifft1_A7))
                trace["ifft1" + str(ifft1)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles = pc_ifft1_A15))

                # write 1 token to Windowing
                for wind in range(self.num_ph1):
                    trace["ifft1" + str(ifft1)]["ARM_CORTEX_A7"].\
                    append(TraceSegment(process_cycles=0,
                    write_to_channel="ifft1" + str(ifft1) + "_" + "wind" + str(wind),
                    n_tokens=1))
                    trace["ifft1" + str(ifft1)]["ARM_CORTEX_A15"].\
                    append(TraceSegment(process_cycles=0,
                    write_to_channel="ifft1" + str(ifft1) + "_" + "wind" + str(wind),
                    n_tokens=1))

            # Windowing tasks
            for wind in range(self.num_ph1):
                # read 1 token from IFFT1
                for ifft1 in range(self.num_ph1):
                    trace["wind" + str(wind)]["ARM_CORTEX_A7"].\
                    append(TraceSegment(process_cycles=0,
                    read_from_channel="ifft1" + str(ifft1) + "_" + "wind" + str(wind),
                    n_tokens=1))
                    trace["wind" + str(wind)]["ARM_CORTEX_A15"].\
                    append(TraceSegment(process_cycles=0,
                    read_from_channel="ifft1" + str(ifft1) + "_" + "wind" + str(wind),
                    n_tokens=1))

                # Process tasks
                trace["wind" + str(wind)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles = pc_wind_A7))
                trace["wind" + str(wind)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles = pc_wind_A15))

                # write 1 token to FFT
                for fft in range(self.num_ph1):
                    trace["wind" + str(wind)]["ARM_CORTEX_A7"].\
                    append(TraceSegment(process_cycles=0,
                    write_to_channel="wind" + str(wind) + "_" + "fft" + str(fft),
                    n_tokens=1))
                    trace["wind" + str(wind)]["ARM_CORTEX_A15"].\
                    append(TraceSegment(process_cycles=0,
                    write_to_channel="wind" + str(wind) + "_" + "fft" + str(fft),
                    n_tokens=1))

            # FFT tasks
            for fft in range(self.num_ph1):
                # read 1 token from IFFT1
                for wind in range(self.num_ph1):
                    trace["fft" + str(fft)]["ARM_CORTEX_A7"].\
                    append(TraceSegment(process_cycles=0,
                    read_from_channel="wind" + str(wind) + "_" + "fft" + str(fft),
                    n_tokens=1))
                    trace["fft" + str(fft)]["ARM_CORTEX_A15"].\
                    append(TraceSegment(process_cycles=0,
                    read_from_channel="wind" + str(wind) + "_" + "fft" + str(fft),
                    n_tokens=1))

                # Process tasks
                trace["fft" + str(fft)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles = pc_fft_A7))
                trace["fft" + str(fft)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles = pc_fft_A15))

                # write 1 token to FFT
                for comb in range(self.num_ph2):
                    trace["fft" + str(fft)]["ARM_CORTEX_A7"].\
                    append(TraceSegment(process_cycles=0,
                    write_to_channel="fft" + str(fft) + "_" + "comb" + str(comb),
                    n_tokens=1))
                    trace["fft" + str(fft)]["ARM_CORTEX_A15"].\
                    append(TraceSegment(process_cycles=0,
                    write_to_channel="fft" + str(fft) + "_" + "comb" + str(comb),
                    n_tokens=1))

            # CombW tasks
            for comb in range(self.num_ph2):
                # read 1 token from FFT
                for fft in range(self.num_ph1):
                    trace["comb" + str(comb)]["ARM_CORTEX_A7"].\
                    append(TraceSegment(process_cycles=0,
                    read_from_channel="fft" + str(fft) + "_" + "comb" + str(comb),
                    n_tokens=1))
                    trace["comb" + str(comb)]["ARM_CORTEX_A15"].\
                    append(TraceSegment(process_cycles=0,
                    read_from_channel="fft" + str(fft) + "_" + "comb" + str(comb),
                    n_tokens=1))

                # Process tasks
                trace["comb" + str(comb)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles = pc_comb_A7))
                trace["comb" + str(comb)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles = pc_comb_A15))

                # write 1 token to AntComb
                for ant in range(self.num_ph3):
                    trace["comb" + str(comb)]["ARM_CORTEX_A7"].\
                    append(TraceSegment(process_cycles=0,
                    write_to_channel="comb" + str(comb) + "_" + "ant" + str(ant),
                    n_tokens=1))
                    trace["comb" + str(comb)]["ARM_CORTEX_A15"].\
                    append(TraceSegment(process_cycles=0,
                    write_to_channel="comb" + str(comb) + "_" + "ant" + str(ant),
                    n_tokens=1))

            # AntComb tasks
            for ant in range(self.num_ph3):
                # read 1 token from input
                trace["ant" + str(ant)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles=0,
                read_from_channel="input" + "_" + "ant" + str(ant),
                n_tokens=1))
                trace["ant" + str(ant)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles=0,
                read_from_channel="input" + "_" + "ant" + str(ant),
                n_tokens=1))

                # read 1 token from CombW
                for comb in range(self.num_ph2):
                    trace["ant" + str(ant)]["ARM_CORTEX_A7"].\
                    append(TraceSegment(process_cycles=0,
                    read_from_channel="comb" + str(comb) + "_" + "ant" + str(ant),
                    n_tokens=1))
                    trace["ant" + str(ant)]["ARM_CORTEX_A15"].\
                    append(TraceSegment(process_cycles=0,
                    read_from_channel="comb" + str(comb) + "_" + "ant" + str(ant),
                    n_tokens=1))

                # Process tasks
                trace["ant" + str(ant)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles = pc_ant_A7))
                trace["ant" + str(ant)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles = pc_ant_A15))

                # write 1 token to IFFT2
                for ifft2 in range(self.num_ph3):
                    trace["ant" + str(ant)]["ARM_CORTEX_A7"].\
                    append(TraceSegment(process_cycles=0,
                    write_to_channel="ant" + str(ant) + "_" + "ifft2" + str(ifft2),
                    n_tokens=1))
                    trace["ant" + str(ant)]["ARM_CORTEX_A15"].\
                    append(TraceSegment(process_cycles=0,
                    write_to_channel="ant" + str(ant) + "_" + "ifft2" + str(ifft2),
                    n_tokens=1))

            # IFFT2 tasks
            for ifft2 in range(self.num_ph3):
                # read 1 token from AntComb
                for ant in range(self.num_ph3):
                    trace["ifft2" + str(ifft2)]["ARM_CORTEX_A7"].\
                    append(TraceSegment(process_cycles=0,
                    read_from_channel="ant" + str(ant) + "_" + "ifft2" + str(ifft2),
                    n_tokens=1))
                    trace["ifft2" + str(ifft2)]["ARM_CORTEX_A15"].\
                    append(TraceSegment(process_cycles=0,
                    read_from_channel="ant" + str(ant) + "_" + "ifft2" + str(ifft2),
                    n_tokens=1))

                # Process tasks
                trace["ifft2" + str(ifft2)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles = pc_ifft2_A7))
                trace["ifft2" + str(ifft2)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles = pc_ifft2_A15))

                # write 1 token to Windowing
                for demap in range(self.num_ph4):
                    trace["ifft2" + str(ifft2)]["ARM_CORTEX_A7"].\
                    append(TraceSegment(process_cycles=0,
                    write_to_channel="ifft2" + str(ifft2) + "_" + "demap" + str(demap),
                    n_tokens=1))
                    trace["ifft2" + str(ifft2)]["ARM_CORTEX_A15"].\
                    append(TraceSegment(process_cycles=0,
                    write_to_channel="ifft2" + str(ifft2) + "_" + "demap" + str(demap),
                    n_tokens=1))

        # Demap tasks
        for demap in range(self.num_ph4):
            trace["demap" + str(demap)] = {}
            trace["demap" + str(demap)]["ARM_CORTEX_A7"] = list()
            trace["demap" + str(demap)]["ARM_CORTEX_A15"] = list()

            # read 2 tokens from IFFT2
            for ifft2 in range(self.num_ph3):
                trace["demap" + str(demap)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles=0,
                read_from_channel="ifft2" + str(ifft2) + "_" + "demap" + str(demap),
                n_tokens=2))
                trace["demap" + str(demap)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles=0,
                read_from_channel="ifft2" + str(ifft2) + "_" + "demap" + str(demap),
                n_tokens=2))

            # Process tasks
            trace["demap" + str(demap)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles = pc_demap_A7))
            trace["demap" + str(demap)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles = pc_demap_A15))

            # write 1 token to output
            trace["demap" + str(demap)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles=0,
            write_to_channel="demap" + str(demap) + "_" + "output",
            n_tokens=1))
            trace["demap" + str(demap)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles=0,
            write_to_channel="demap" + str(demap) + "_" + "output",
            n_tokens=1))

        # Output task
        # read 1 token from Demap
        for demap in range(self.num_ph4):
            trace["output"]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles=0,
            read_from_channel="demap" + str(demap) + "_" + "output",
            n_tokens=1))
            trace["output"]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles=0,
            read_from_channel="demap" + str(demap) + "_" + "output",
            n_tokens=1))

        # terminate all tasks
        trace["input"]["ARM_CORTEX_A7"].\
        append(TraceSegment(process_cycles=0, terminate=True))
        trace["input"]["ARM_CORTEX_A15"].\
        append(TraceSegment(process_cycles=0, terminate=True))
        for mf in range(self.num_ph1):
            trace["mf" + str(mf)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles=0, terminate=True))
            trace["mf" + str(mf)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles=0, terminate=True))
        for ifft1 in range(self.num_ph1):
            trace["ifft1" + str(ifft1)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles=0, terminate=True))
            trace["ifft1" + str(ifft1)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles=0, terminate=True))
        for wind in range(self.num_ph1):
            trace["wind" + str(wind)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles=0, terminate=True))
            trace["wind" + str(wind)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles=0, terminate=True))
        for fft in range(self.num_ph1):
            trace["fft" + str(fft)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles=0, terminate=True))
            trace["fft" + str(fft)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles=0, terminate=True))
        for comb in range(self.num_ph2):
            trace["comb" + str(comb)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles=0, terminate=True))
            trace["comb" + str(comb)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles=0, terminate=True))
        for ant in range(self.num_ph3):
            trace["ant" + str(ant)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles=0, terminate=True))
            trace["ant" + str(ant)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles=0, terminate=True))
        for ifft2 in range(self.num_ph3):
            trace["ifft2" + str(ifft2)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles=0, terminate=True))
            trace["ifft2" + str(ifft2)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles=0, terminate=True))
        for demap in range(self.num_ph4):
            trace["demap" + str(demap)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles=0, terminate=True))
            trace["demap" + str(demap)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles=0, terminate=True))
        trace["output"]["ARM_CORTEX_A7"].\
        append(TraceSegment(process_cycles=0, terminate=True))
        trace["output"]["ARM_CORTEX_A15"].\
        append(TraceSegment(process_cycles=0, terminate=True))

        self.trace = trace

        # we also need to keep track of the current position in the trace
        self.trace_pos = {}

        self.trace_pos["input"] = 0
        self.trace_pos["output"] = 0
        for ph1 in range(self.num_ph1):
            self.trace_pos["mf" + str(ph1)] = 0
            self.trace_pos["ifft1" + str(ph1)] = 0
            self.trace_pos["wind" + str(ph1)] = 0
            self.trace_pos["fft" + str(ph1)] = 0
        for ph2 in range(self.num_ph2):
            self.trace_pos["comb" + str(ph2)] = 0
        for ph3 in range(self.num_ph3):
            self.trace_pos["ant" + str(ph3)] = 0
            self.trace_pos["ifft2" + str(ph3)] = 0
        for ph4 in range(self.num_ph4):
            self.trace_pos["demap" + str(ph4)] = 0

    def reset(self):
        self.trace_pos["input"] = 0
        self.trace_pos["output"] = 0
        for ph1 in range(self.num_ph1):
            self.trace_pos["mf" + str(ph1)] = 0
            self.trace_pos["ifft1" + str(ph1)] = 0
            self.trace_pos["wind" + str(ph1)] = 0
            self.trace_pos["fft" + str(ph1)] = 0
        for ph2 in range(self.num_ph2):
            self.trace_pos["comb" + str(ph2)] = 0
        for ph3 in range(self.num_ph3):
            self.trace_pos["ant" + str(ph3)] = 0
            self.trace_pos["ifft2" + str(ph3)] = 0
        for ph4 in range(self.num_ph4):
            self.trace_pos["demap" + str(ph4)] = 0

    def next_segment(self, process_name, processor_type):
        pos = self.trace_pos[process_name]
        self.trace_pos[process_name] = pos + 1
        return self.trace[process_name][processor_type][pos]

class FiveGSimulation(BaseSimulation):
    """Simulate the processing of 5G data"""

    def __init__(self, platform, cfg, trace_file, task_file, **kwargs):
        super().__init__(platform)
        self.cfg = cfg

        # Get lte traces
        self.TFM = TraceFileManager(trace_file)
        self.ntrace = TraceFileManager.Trace()

        # Get task execution time info
        self.proc_time = get_task_time(task_file)

    @staticmethod
    def from_hydra(cfg, **kwargs):
        platform = hydra.utils.instantiate(cfg['platform'])
        return FiveGSimulation(platform, cfg, **kwargs)

    def _manager_process(self):
        trace_writer = self.system.trace_writer

        app_finished = []
        criticalities = []
        prbs = []
        mod = []

        i = 0
        cnt = 0
        # while end of file not reached:
        while self.TFM.TF_EOF is not True:
            
            nsubframe = self.TFM.get_next_subframe()

            # create a new mapper (this should be TETRiS in the future) Note
            # that we need to create a new mapper here, as the KPN could change
            # This appears to be a weakness of our mapper interface. The KPN
            # should probably become a parameter of generate_mapping().
            mapper = StaticCFSMapperMultiApp(self.platform)
            # run 100 instances of the 5G app, start one every 1 ms
            kpns = []
            traces = []
            for ntrace in nsubframe.trace:
                # create a new graph and trace
                self.ntrace = ntrace

                kpns.append(FivegGraph(i,self.ntrace))
                traces.append(FivegTraceGenerator(self.ntrace, self.proc_time))
                i += 1
                criticalities.append(ntrace.UE_criticality)
                prbs.append(ntrace.PRBs)
                mod.append(ntrace.modulation_scheme)

            mappings = mapper.generate_mappings(kpns,traces) #TODO: collect and add load here

            for mapping,trace in zip(mappings,traces):
                # instantiate the application
                app = FiveGRuntimeKpnApplication(name=mapping.kpn.name,
                                                        kpn_graph=mapping.kpn,
                                                        mapping=mapping,
                                                        trace_generator=trace,
                                                        system=self.system)
                # record application start in the simulation trace
                trace_writer.begin_duration("instances", app.name, app.name)
                # start the application
                finished = self.env.process(app.run_app(criticalities[cnt],prbs[cnt],mod[cnt]))
                cnt += 1
                # register a callback to record the application termination
                # in the simulation trace
                finished.callbacks.append(
                    lambda _, name=app.name: trace_writer.end_duration(
                        "instances", name, name))
                # keep the finished event for later
                app_finished.append(finished)

            # wait for 1 ms
            yield self.env.timeout(1000000000)           
    
        # wait until all applications finished
        yield self.env.all_of(app_finished)

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
        # check if all kpn processes finished execution
        self.system.check_errors()
        # save the execution time
        self.exec_time = self.env.now


class FiveGRuntimeKpnApplication(RuntimeKpnApplication):

    def run_app(self, criticality, prbs, mod):
        """Start execution of this application

        Yields:
            ~simpy.events.Event: an event that is triggered when the
                application finishes execution.
        """

        IOT = 0
        AVT = 0
        EMBB = 0
        missIOT = 0
        missAVT = 0
        missEMBB = 0
        drop = False

        if criticality == 0:
            IOT = 1
            timeout = 2500000000
        elif criticality == 1:
            AVT = 1
            timeout = 500000000
        elif criticality == 2:
            EMBB = 1
            timeout = 2500000000

        self._log.info(f"Application {self.name} starts")
        start = self.env.now

        for process, mapping_info in self._mapping_infos.items():
            self.system.start_process(process, mapping_info)
        finished = self.env.all_of([p.finished for p in self.processes()])
        finished.callbacks.append(lambda _: self._log.info(
            f"Application {self.name} terminates"))
        yield finished | self.env.timeout(timeout)

        #if finished.ok and 
        if not finished.processed:
            drop = True

        end = self.env.now

        if drop:
            if criticality == 0:
                missIOT = 1
            elif criticality == 1:
                missAVT = 1
            elif criticality == 2:
                missEMBB = 1

        print(str(IOT) +
              "," + str(AVT) +
              "," + str(EMBB) +
              "," + str(missIOT) +
              "," + str(missAVT) +
              "," + str(missEMBB) +
              "," + str(start) +
              "," + str(end) +
              "," + str(criticality) +
              "," + str(prbs) + 
              "," + str(mod)
        )

        if drop:
            self.kill()

