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

        # Number of tasks of each type
        self.micf = PHY.get_num_micf( ntrace.layers)
        self.combwc = PHY.get_num_combwc()
        self.antcomb = PHY.get_num_antcomb(ntrace.layers)
        self.demap = PHY.get_num_demap()

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

        if nmbSc <-16:
            fft_size = 8
        elif nmbSc <= 32:
            fft_size = 16
        elif nmbSc <= 64:
            fft_size = 32
        elif nmbSc <= 128:
            fft_size = 64
        elif nmbSc <= 256:
            fft_size = 128
        elif nmbSc <= 512:
            fft_size = 256
        elif nmbSc <= 600:
            fft_size = 300
        elif nmbSc <= 1024:
            fft_size = 512
        elif nmbSc <= 1200:
            fft_size = 600
    
        # dictionary for processes
        pmicf = {}
        pcombwc = {}
        pantcomb = {}
        pdemap = {}

        # dictionary for channels
        iConn = {} # input
        oConn = {} # output
        aConn = {}
        bConn = {}
        cConn = {}

        # add process to dictionary
        src = KpnProcess("src")
        sink = KpnProcess("sink")
        for nmicf in range(self.micf):
            process = "micf_" + str(nmicf)
            pmicf[process] = KpnProcess(process)
        for ncombwc in range(self.combwc):
            process = "combwc_" + str(ncombwc)
            pcombwc[process] = KpnProcess(process)
        for nantcomb in range(self.antcomb):
            process = "antcomb_" + str(nantcomb)
            pantcomb[process] = KpnProcess(process)
        for ndemap in range(self.demap):
            process = "demap_" + str(ndemap)
            pdemap[process] = KpnProcess(process)

        # add channels to dictionary and connect processes
        for nmicf in range(self.micf):
            dest = "micf_" + str(nmicf)
            channel = "i_m_" + str(nmicf)
            iConn[channel] = KpnChannel(channel, data_size*(sc*prbs*2+fft_size))
            src.connect_to_outgoing_channel(iConn[channel])
            pmicf[dest].connect_to_incomming_channel(iConn[channel])
        for nantcomb in range(self.antcomb):
            dest = "antcomb_" + str(nantcomb)
            channel = "i_a_" + str(nantcomb)
            iConn[channel] = KpnChannel(channel, data_size*(nmbSc*lay+fft_size))
            src.connect_to_outgoing_channel(iConn[channel])
            pantcomb[dest].connect_to_incomming_channel(iConn[channel])
        for nmicf in range(self.micf):
            for ncombwc in range(self.combwc):
                origin = "micf_" + str(nmicf)
                dest = "combwc_" + str(ncombwc)
                channel = "a_" + str(nmicf) + "_" + str(ncombwc)
                aConn[channel] = KpnChannel(channel, data_size*prbs)
                pmicf[origin].connect_to_outgoing_channel(aConn[channel])
                pcombwc[dest].connect_to_incomming_channel(aConn[channel])
        for ncombwc in range(self.combwc):
            for nantcomb in range(self.antcomb):
                origin = "combwc_" + str(ncombwc)
                dest = "antcomb_" + str(nantcomb)
                channel = "b_" + str(ncombwc) + "_" + str(nantcomb)
                bConn[channel] = KpnChannel(channel, data_size*prbs*ant)
                pcombwc[origin].connect_to_outgoing_channel(bConn[channel])
                pantcomb[dest].connect_to_incomming_channel(bConn[channel])
        for nantcomb in range(self.antcomb):
            for ndemap in range(self.demap):
                origin = "antcomb_" + str(nantcomb)
                dest = "demap_" + str(ndemap)
                channel = "c_" + str(nantcomb) + \
                        "_" + str(ndemap)
                cConn[channel] = KpnChannel(channel, data_size*prbs)
                pantcomb[origin].connect_to_outgoing_channel(cConn[channel])
                pdemap[dest].connect_to_incomming_channel(cConn[channel])
        for ndemap in range(self.demap):
            origin = "demap_" + str(ndemap)
            channel = "o_d_" + str(ndemap)
            oConn[channel] = KpnChannel(channel, data_size*prbs*mod)
            pdemap[origin].connect_to_outgoing_channel(oConn[channel])
            sink.connect_to_incomming_channel(oConn[channel])

        # register all processes
        self.add_process(src)
        self.add_process(sink)
        for nmicf in range(self.micf):
            process = "micf_" + str(nmicf)
            self.add_process(pmicf[process])
        for ncombwc in range(self.combwc):
            process = "combwc_" + str(ncombwc)
            self.add_process(pcombwc[process])
        for nantcomb in range(self.antcomb):
            process = "antcomb_" + str(nantcomb)
            self.add_process(pantcomb[process])
        for ndemap in range(self.demap):
            process = "demap_" + str(ndemap)
            self.add_process(pdemap[process])          

        # register all channels
        for nmicf in range(self.micf):
            channel = "i_m_" + str(nmicf)
            self.add_channel(iConn[channel])
        for nantcomb in range(self.antcomb):
            channel = "i_a_" + str(nantcomb)
            self.add_channel(iConn[channel])
        for nmicf in range(self.micf):
            for ncombwc in range(self.combwc):
                channel = "a_" + str(nmicf) + "_" + str(ncombwc)
                self.add_channel(aConn[channel])
        for ncombwc in range(self.combwc):
            for nantcomb in range(self.antcomb):
                channel = "b_" + str(ncombwc) + "_" + str(nantcomb)
                self.add_channel(bConn[channel])
        for nantcomb in range(self.antcomb):
            for ndemap in range(self.demap):
                channel = "c_" + str(nantcomb) + "_" + str(ndemap)
                self.add_channel(cConn[channel])
        for ndemap in range(self.demap):
            channel = "o_d_" + str(ndemap)
            self.add_channel(oConn[channel])


class FivegTraceGenerator(TraceGenerator):
    """Generates traces for the 5G application
    """

    def __init__(self, ntrace, proc_time):
        # build a dictionary of all the traces
        trace = {}
        
        # Number of tasks of each type
        self.micf = PHY.get_num_micf( ntrace.layers)
        self.combwc = PHY.get_num_combwc()
        self.antcomb = PHY.get_num_antcomb(ntrace.layers)
        self.demap = PHY.get_num_demap()
        
        # number of PRBs
        prbs = ntrace.PRBs
        # modulation scheme
        mod = ntrace.modulation_scheme

        # clock frequency for core types Cortex A7 and Cortex15
        freq_arm_cortex_a7 = 1300000000
        freq_arm_cortex_a15 = 2000000000

        # process cycles for each task type on ARM_CORTEX_A7
        pc_micf_A7 = proc_time[0][prbs - 1] * freq_arm_cortex_a7
        pc_combwc_A7 = proc_time[0][prbs + 100 -1] * freq_arm_cortex_a7
        pc_antcomb_A7 = proc_time[0][prbs + 200 - 1] * freq_arm_cortex_a7
        pc_demap_A7 = proc_time[0][prbs + (300 + 100 * mod) - 1] * \
                    freq_arm_cortex_a7
        
        # process cycles for each task type on ARM_CORTEX_A15
        pc_micf_A15 = proc_time[0][prbs - 1] * freq_arm_cortex_a15
        pc_combwc_A15 = proc_time[0][prbs + 100 - 1] * freq_arm_cortex_a15
        pc_antcomb_A15 = proc_time[0][prbs + 200 - 1] * freq_arm_cortex_a15
        pc_demap_A15 = proc_time[0][prbs + (300 + 100 * mod) - 1] * \
                    freq_arm_cortex_a15

        trace["src"] = {}
        trace["src"]["ARM_CORTEX_A7"] = list()
        trace["src"]["ARM_CORTEX_A15"] = list()
        trace["sink"] = {}
        trace["sink"]["ARM_CORTEX_A7"] = list()
        trace["sink"]["ARM_CORTEX_A15"] = list()

        for nmicf in range(self.micf):
            # write 1 token from channel
            trace["src"]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles=0,
            write_to_channel="i_m_" + str(nmicf),
            n_tokens=1))
            trace["src"]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles=0,
            write_to_channel="i_m_" + str(nmicf),
            n_tokens=1))

        for nantcomb in range(self.antcomb):
            # write 1 token from channel
            trace["src"]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles=0,
            write_to_channel="i_a_" + str(nantcomb),
            n_tokens=1))
            trace["src"]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles=0,
            write_to_channel="i_a_" + str(nantcomb),
            n_tokens=1))

        for nmicf in range(self.micf):
            trace["micf_" + str(nmicf)] = {}
            trace["micf_" + str(nmicf)]["ARM_CORTEX_A7"] = list()
            trace["micf_" + str(nmicf)]["ARM_CORTEX_A15"] = list()

            # read 1 token from channel
            trace["micf_" + str(nmicf)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles=0,
            read_from_channel="i_m_" + str(nmicf),
            n_tokens=1))
            trace["micf_" + str(nmicf)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles=0,
            read_from_channel="i_m_" + str(nmicf),
            n_tokens=1))

            # Process tasks
            trace["micf_" + str(nmicf)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles = pc_micf_A7))
            trace["micf_" + str(nmicf)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles = pc_micf_A15))

            # write 1 token to channel
            for ncombwc in range(self.combwc):
                trace["micf_" + str(nmicf)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles=0, 
                write_to_channel="a_" + str(nmicf) + "_" + str(ncombwc),
                n_tokens=1))
                trace["micf_" + str(nmicf)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles=0, 
                write_to_channel="a_" + str(nmicf) + "_" + str(ncombwc),
                n_tokens=1))

        for ncombwc in range(self.combwc):
            trace["combwc_" + str(ncombwc)] = {}
            trace["combwc_" + str(ncombwc)]["ARM_CORTEX_A7"] = list()
            trace["combwc_" + str(ncombwc)]["ARM_CORTEX_A15"] = list()

            # read 1 token from channel
            for nmicf in range(self.micf):
                trace["combwc_" + str(ncombwc)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles=0, 
                read_from_channel="a_" + str(nmicf) + "_" + str(ncombwc),
                n_tokens=1))
                trace["combwc_" + str(ncombwc)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles=0, 
                read_from_channel="a_" + str(nmicf) + "_" + str(ncombwc),
                n_tokens=1))

            # Process tasks
            trace["combwc_" + str(ncombwc)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles = pc_combwc_A7))
            trace["combwc_" + str(ncombwc)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles = pc_combwc_A15))

            # write 1 token to channel
            for nantcomb in range(self.antcomb):
                trace["combwc_" + str(ncombwc)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles=0, 
                write_to_channel="b_" + str(ncombwc) + "_" + str(nantcomb),
                n_tokens=1))
                trace["combwc_" + str(ncombwc)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles=0, 
                write_to_channel="b_" + str(ncombwc) + "_" + str(nantcomb),
                n_tokens=1))

        for nantcomb in range(self.antcomb):
            trace["antcomb_" + str(nantcomb)] = {}
            trace["antcomb_" + str(nantcomb)]["ARM_CORTEX_A7"] = list()
            trace["antcomb_" + str(nantcomb)]["ARM_CORTEX_A15"] = list()

            # read 1 token from channel
            trace["antcomb_" + str(nantcomb)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles=0,
            read_from_channel="i_a_" + str(nantcomb),
            n_tokens=1))
            trace["antcomb_" + str(nantcomb)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles=0,
            read_from_channel="i_a_" + str(nantcomb),
            n_tokens=1))

            # read 1 token from channel
            for ncombwc in range(self.combwc):
                trace["antcomb_" + str(nantcomb)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles=0, 
                read_from_channel="b_" + str(ncombwc) + "_" + str(nantcomb),
                n_tokens=1))
                trace["antcomb_" + str(nantcomb)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles=0, 
                read_from_channel="b_" + str(ncombwc) + "_" + str(nantcomb),
                n_tokens=1))

            # Process tasks
            trace["antcomb_" + str(nantcomb)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles = pc_antcomb_A7))
            trace["antcomb_" + str(nantcomb)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles = pc_antcomb_A15))

            # write 1 token to channel
            for ndemap in range(self.demap):
                trace["antcomb_" + str(nantcomb)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles=0, 
                write_to_channel="c_" + str(nantcomb) + "_" + str(ndemap),
                n_tokens=1))
                trace["antcomb_" + str(nantcomb)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles=0, 
                write_to_channel="c_" + str(nantcomb) + "_" + str(ndemap),
                n_tokens=1))

        for nmicf in range(self.micf):
            # write 1 token from channel
            trace["src"]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles=0,
            write_to_channel="i_m_" + str(nmicf),
            n_tokens=1))
            trace["src"]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles=0,
            write_to_channel="i_m_" + str(nmicf),
            n_tokens=1))

        for nantcomb in range(self.antcomb):
            # write 1 token from channel
            trace["src"]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles=0,
            write_to_channel="i_a_" + str(nantcomb),
            n_tokens=1))
            trace["src"]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles=0,
            write_to_channel="i_a_" + str(nantcomb),
            n_tokens=1))

        # terminate
        trace["src"]["ARM_CORTEX_A7"].\
        append(TraceSegment(process_cycles=0, terminate=True))
        trace["src"]["ARM_CORTEX_A15"].\
        append(TraceSegment(process_cycles=0, terminate=True))

        for nmicf in range(self.micf):

            # read 1 token from channel
            trace["micf_" + str(nmicf)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles=0,
            read_from_channel="i_m_" + str(nmicf),
            n_tokens=1))
            trace["micf_" + str(nmicf)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles=0,
            read_from_channel="i_m_" + str(nmicf),
            n_tokens=1))

            # Process tasks
            trace["micf_" + str(nmicf)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles = pc_micf_A7))
            trace["micf_" + str(nmicf)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles = pc_micf_A15))

            # write 1 token to channel
            for ncombwc in range(self.combwc):
                trace["micf_" + str(nmicf)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles=0, 
                write_to_channel="a_" + str(nmicf) + "_" + str(ncombwc),
                n_tokens=1))
                trace["micf_" + str(nmicf)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles=0, 
                write_to_channel="a_" + str(nmicf) + "_" + str(ncombwc),
                n_tokens=1))

            # terminate
            trace["micf_" + str(nmicf)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles=0, terminate=True))
            trace["micf_" + str(nmicf)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles=0, terminate=True))

        for ncombwc in range(self.combwc):

            # read 1 token from channel
            for nmicf in range(self.micf):
                trace["combwc_" + str(ncombwc)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles=0, 
                read_from_channel="a_" + str(nmicf) + "_" + str(ncombwc),
                n_tokens=1))
                trace["combwc_" + str(ncombwc)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles=0, 
                read_from_channel="a_" + str(nmicf) + "_" + str(ncombwc),
                n_tokens=1))

            # Process tasks
            trace["combwc_" + str(ncombwc)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles = pc_combwc_A7))
            trace["combwc_" + str(ncombwc)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles = pc_combwc_A15))

            # write 1 token to channel
            for nantcomb in range(self.antcomb):
                trace["combwc_" + str(ncombwc)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles=0, 
                write_to_channel="b_" + str(ncombwc) + "_" + str(nantcomb),
                n_tokens=1))
                trace["combwc_" + str(ncombwc)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles=0, 
                write_to_channel="b_" + str(ncombwc) + "_" + str(nantcomb),
                n_tokens=1))

            # terminate
            trace["combwc_" + str(ncombwc)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles=0, terminate=True))
            trace["combwc_" + str(ncombwc)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles=0, terminate=True))
            
        for nantcomb in range(self.antcomb):

            # read 1 token from channel
            trace["antcomb_" + str(nantcomb)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles=0,
            read_from_channel="i_a_" + str(nantcomb),
            n_tokens=1))
            trace["antcomb_" + str(nantcomb)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles=0,
            read_from_channel="i_a_" + str(nantcomb),
            n_tokens=1))

            # read 1 token from channel
            for ncombwc in range(self.combwc):
                trace["antcomb_" + str(nantcomb)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles=0, 
                read_from_channel="b_" + str(ncombwc) + "_" + str(nantcomb),
                n_tokens=1))
                trace["antcomb_" + str(nantcomb)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles=0, 
                read_from_channel="b_" + str(ncombwc) + "_" + str(nantcomb),
                n_tokens=1))

            # Process tasks
            trace["antcomb_" + str(nantcomb)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles = pc_antcomb_A7))
            trace["antcomb_" + str(nantcomb)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles = pc_antcomb_A15))

            # write 1 token to channel
            for ndemap in range(self.demap):
                trace["antcomb_" + str(nantcomb)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles=0, 
                write_to_channel="c_" + str(nantcomb) + "_" + str(ndemap),
                n_tokens=1))
                trace["antcomb_" + str(nantcomb)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles=0, 
                write_to_channel="c_" + str(nantcomb) + "_" + str(ndemap),
                n_tokens=1))

            # terminate
            trace["antcomb_" + str(nantcomb)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles=0, terminate=True))
            trace["antcomb_" + str(nantcomb)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles=0, terminate=True))

        for ndemap in range(self.demap):
            trace["demap_" + str(ndemap)] = {}
            trace["demap_" + str(ndemap)]["ARM_CORTEX_A7"] = list()
            trace["demap_" + str(ndemap)]["ARM_CORTEX_A15"] = list()

            # read 2 tokens from channel
            for nantcomb in range(self.antcomb):
                trace["demap_" + str(ndemap)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles=0,
                read_from_channel="c_" + str(nantcomb) + "_" + str(ndemap),
                n_tokens=2))
                trace["demap_" + str(ndemap)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles=0, 
                read_from_channel="c_" + str(nantcomb) + "_" + str(ndemap),
                n_tokens=2))

            # Process tasks
            trace["demap_" + str(ndemap)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles = pc_demap_A7))
            trace["demap_" + str(ndemap)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles = pc_demap_A15))

            # write 1 token to channel
            trace["demap_" + str(ndemap)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles=0,
            write_to_channel="o_d_" + str(ndemap),
            n_tokens=1))
            trace["demap_" + str(ndemap)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles=0,
            write_to_channel="o_d_" + str(ndemap),
            n_tokens=1))

            # terminate
            trace["demap_" + str(ndemap)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles=0, terminate=True))
            trace["demap_" + str(ndemap)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles=0, terminate=True))

        # read 1 token from channel
        for ndemap in range(self.demap):
            trace["sink"]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles=0,
            read_from_channel="o_d_" + str(ndemap),
            n_tokens=1))
            trace["sink"]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles=0,
            read_from_channel="o_d_" + str(ndemap),
            n_tokens=1))

        # terminate
        trace["sink"]["ARM_CORTEX_A7"].\
        append(TraceSegment(process_cycles=0, terminate=True))
        trace["sink"]["ARM_CORTEX_A15"].\
        append(TraceSegment(process_cycles=0, terminate=True))

        self.trace = trace

        # we also need to keep track of the current position in the trace
        self.trace_pos = {}

        self.trace_pos["src"] = 0
        self.trace_pos["sink"] = 0
        for nmicf in range(self.micf):
            self.trace_pos["micf_" + str(nmicf)] = 0
        for ncombwc in range(self.combwc):
            self.trace_pos["combwc_" + str(ncombwc)] = 0
        for nantcomb in range(self.antcomb):
            self.trace_pos["antcomb_" + str(nantcomb)] = 0
        for ndemap in range(self.demap):
            self.trace_pos["demap_" + str(ndemap)] = 0

    def reset(self):
        self.trace_pos = {}
        self.trace_pos["src"] = 0
        self.trace_pos["sink"] = 0
        for nmicf in range(self.micf):
            self.trace_pos["micf_" + str(nmicf)] = 0
        for ncombwc in range(self.combwc):
            self.trace_pos["combwc_" + str(ncombwc)] = 0
        for nantcomb in range(self.antcomb):
            self.trace_pos["antcomb_" + str(nantcomb)] = 0
        for ndemap in range(self.demap):
            self.trace_pos["demap_" + str(ndemap)] = 0

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

        i = 0
        # while end of file not reached:
        while self.TFM.TF_EOF is not True:
            
            nsubframe = self.TFM.get_next_subframe()

            # create a new mapper (this should be TETRiS in the future) Note
            # that we need to create a new mapper here, as the KPN could change
            # This appears to be a weakness of our mapper interface. The KPN
            # should probably become a parameter of generate_mapping().
            mapper = StaticCFSMapperMultiApp(self.platform,self.cfg)
            # run 100 instances of the 5G app, start one every 1 ms
            kpns = []
            traces = []
            for ntrace in nsubframe.trace:
                # create a new graph and trace
                self.ntrace = ntrace

                kpns.append(FivegGraph(i,self.ntrace))
                traces.append(FivegTraceGenerator(self.ntrace, self.proc_time))
                i += 1
            mappings = mapper.generate_mappings(kpns,traces) #TODO: collect and add load here

            for mapping,trace in zip(mappings,traces):
                # instantiate the application
                app = RuntimeKpnApplication(name=mapping.kpn.name,
                                            kpn_graph=mapping.kpn,
                                            mapping=mapping,
                                            trace_generator=trace,
                                            system=self.system)
                # record application start in the simulation trace
                trace_writer.begin_duration("instances", app.name, app.name)
                # start the application
                finished = self.env.process(app.run())
                # register a callback to record the application terminatation
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
