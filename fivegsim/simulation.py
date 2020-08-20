import hydra

from pykpn.mapper.random import RandomMapper
from pykpn.common.kpn import KpnGraph, KpnProcess, KpnChannel
from pykpn.common.trace import TraceGenerator, TraceSegment
from pykpn.simulate import BaseSimulation
from pykpn.simulate.application import RuntimeKpnApplication

from fivegsim.useful_files.trace_file_manager import TraceFileManager
from fivegsim.useful_files.phybench import PHY
from fivegsim.useful_files.proc_tgff_reader import get_task_time

class params(object):
    """ Useful parameters for 5G application    
    """
    # clock frequency for core types Cortex A7 and Cortex15
    freq_arm_cortex_a7 = 1300000000
    freq_arm_cortex_a15 = 2000000000

    # Number of tasks of each type
    micf = 0
    combwc = 0
    antcomb = 0
    demap = 0

    # Get LTE traces
    trace_file_path = "/Users/julian.robledo/Documents/pykpn/fivegsim/fivegsim/useful_files/"
    trace_file_name = "slicedtrace30BS.txt"
    TFM = TraceFileManager(trace_file_name, trace_file_path)
    ntrace = TraceFileManager.Trace()

    # Get task execution time info
    tgff_proc_path = "/Users/julian.robledo/Documents/pykpn/fivegsim/fivegsim/useful_files/"
    tgff_name = "lte_processors.tgff"
    proc_time = get_task_time(tgff_name, tgff_proc_path)


class FivegGraph(KpnGraph):
    """The KPN graph of a 5G application
    
    The 5G application has the following type of tasks:
    micf, combwc, antcomb, demap.
    """

    def __init__(self):
        super().__init__("fiveg")

        # dictionary for processes
        pmicf = {}
        pcombwc = {}
        pantcomb = {}
        pdemap = {}

        # dictionary for channels
        aConn = {}
        bConn = {}
        cConn = {}
        dConn = {}
        eConn = {}
        fConn = {}

        # add process to dictionary
        for nmicf in range(params.micf*2):
            process = "micf_" + str(nmicf)
            pmicf[process] = KpnProcess(process)
        for ncombwc in range(params.combwc*2):
            process = "combwc_" + str(ncombwc)
            pcombwc[process] = KpnProcess(process)
        for nantcomb in range(params.antcomb*2):
            process = "antcomb_" + str(nantcomb)
            pantcomb[process] = KpnProcess(process)
        for ndemap in range(params.demap):
            process = "demap_" + str(ndemap)
            pdemap[process] = KpnProcess(process)            

        # add channels ((with a token size of 16 bytes each)) to dictionary 
        # and connect the processes
        for nmicf in range(params.micf):
            for ncombwc in range(params.combwc):
                origin = "micf_" + str(nmicf)
                dest = "combwc_" + str(ncombwc)
                channel = "a_" + str(nmicf) + "_" + str(ncombwc)
                aConn[channel] = KpnChannel(channel, 16)
                pmicf[origin].connect_to_outgoing_channel(aConn[channel])
                pcombwc[dest].connect_to_incomming_channel(aConn[channel])
        for ncombwc in range(params.combwc):
            for nantcomb in range(params.antcomb):
                origin = "combwc_" + str(ncombwc)
                dest = "antcomb_" + str(nantcomb)
                channel = "b_" + str(ncombwc) + "_" + str(nantcomb)
                bConn[channel] = KpnChannel(channel, 16)
                pcombwc[origin].connect_to_outgoing_channel(bConn[channel])
                pantcomb[dest].connect_to_incomming_channel(bConn[channel])
        for nantcomb in range(params.antcomb):
            for nmicf in range(params.micf):
                origin = "antcomb_" + str(nantcomb)
                dest = "micf_" + str(nmicf + params.micf)
                channel = "c_" + str(nantcomb) + "_" + str(nmicf + params.micf)
                cConn[channel] = KpnChannel(channel, 16)
                pantcomb[origin].connect_to_outgoing_channel(cConn[channel])
                pmicf[dest].connect_to_incomming_channel(cConn[channel])
        for nmicf in range(params.micf):
            for ncombwc in range(params.combwc):
                origin = "micf_" + str(nmicf + params.micf)
                dest = "combwc_" + str(ncombwc + params.combwc)
                channel = "d_" + str(nmicf + params.micf) + \
                        "_" + str(ncombwc + params.combwc)
                dConn[channel] = KpnChannel(channel, 16)
                pmicf[origin].connect_to_outgoing_channel(dConn[channel])
                pcombwc[dest].connect_to_incomming_channel(dConn[channel])
        for ncombwc in range(params.combwc):
            for nantcomb in range(params.antcomb):
                origin = "combwc_" + str(ncombwc + params.combwc)
                dest = "antcomb_" + str(nantcomb + params.antcomb)
                channel = "e_" + str(ncombwc + params.combwc) + \
                        "_" + str(nantcomb + params.antcomb)
                eConn[channel] = KpnChannel(channel, 16)
                pcombwc[origin].connect_to_outgoing_channel(eConn[channel])
                pantcomb[dest].connect_to_incomming_channel(eConn[channel])
        for nantcomb in range(params.antcomb):
            for ndemap in range(params.demap):
                origin = "antcomb_" + str(nantcomb + params.antcomb)
                dest = "demap_" + str(ndemap)
                channel = "f_" + str(nantcomb + params.antcomb) + \
                        "_" + str(ndemap)
                fConn[channel] = KpnChannel(channel, 16)
                pantcomb[origin].connect_to_outgoing_channel(fConn[channel])
                pdemap[dest].connect_to_incomming_channel(fConn[channel])

        # register all processes
        for nmicf in range(params.micf*2):
            process = "micf_" + str(nmicf)
            self.add_process(pmicf[process])
        for ncombwc in range(params.combwc*2):
            process = "combwc_" + str(ncombwc)
            self.add_process(pcombwc[process])
        for nantcomb in range(params.antcomb*2):
            process = "antcomb_" + str(nantcomb)
            self.add_process(pantcomb[process])
        for ndemap in range(params.demap):
            process = "demap_" + str(ndemap)
            self.add_process(pdemap[process])          

        # register all channels
        for nmicf in range(params.micf):
            for ncombwc in range(params.combwc):
                channel = "a_" + str(nmicf) + "_" + str(ncombwc)
                self.add_channel(aConn[channel])
        for ncombwc in range(params.combwc):
            for nantcomb in range(params.antcomb):
                channel = "b_" + str(ncombwc) + "_" + str(nantcomb)
                self.add_channel(bConn[channel])
        for nantcomb in range(params.antcomb):
            for nmicf in range(params.micf):
                channel = "c_" + str(nantcomb) + \
                        "_" + str(nmicf + params.micf)
                self.add_channel(cConn[channel])
        for nmicf in range(params.micf):
            for ncombwc in range(params.combwc):
                channel = "d_" + str(nmicf + params.micf) + \
                        "_" + str(ncombwc + params.combwc)
                self.add_channel(dConn[channel])
        for ncombwc in range(params.combwc):
            for nantcomb in range(params.antcomb):
                channel = "e_" + str(ncombwc + params.combwc) + \
                        "_" + str(nantcomb + params.antcomb)
                self.add_channel(eConn[channel])
        for nantcomb in range(params.antcomb):
            for ndemap in range(params.demap):
                channel = "f_" + str(nantcomb + params.antcomb) + \
                        "_" + str(ndemap)
                self.add_channel(fConn[channel])


class FivegTraceGenerator(TraceGenerator):
    """Generates traces for the 5G application
    """

    def __init__(self):
        # build a dictionary of all the traces
        trace = {}
        
        # number of PRBs
        prbs = params.ntrace.PRBs
        # modulation scheme
        mod = params.ntrace.modulation_scheme

        # process cycles for each task type on ARM_CORTEX_A7
        pc_micf_A7 = params.proc_time[0][prbs - 1] * \
                    params.freq_arm_cortex_a7
        pc_combwc_A7 = params.proc_time[0][prbs + 100 -1] * \
                    params.freq_arm_cortex_a7
        pc_antcomb_A7 = params.proc_time[0][prbs + 200 - 1] * \
                    params.freq_arm_cortex_a7
        pc_demap_A7 = params.proc_time[0][prbs + (300 + 100 * mod) - 1] * \
                    params.freq_arm_cortex_a7
        
        # process cycles for each task type on ARM_CORTEX_A15
        pc_micf_A15 = params.proc_time[0][prbs - 1] * \
                    params.freq_arm_cortex_a15
        pc_combwc_A15 = params.proc_time[0][prbs + 100 - 1] * \
                    params.freq_arm_cortex_a15
        pc_antcomb_A15 = params.proc_time[0][prbs + 200 - 1] * \
                    params.freq_arm_cortex_a15
        pc_demap_A15 = params.proc_time[0][prbs + (300 + 100 * mod) - 1] * \
                    params.freq_arm_cortex_a15
        

        for nmicf in range(params.micf):
            trace["micf_" + str(nmicf)] = {}
            trace["micf_" + str(nmicf)]["ARM_CORTEX_A7"] = list()
            trace["micf_" + str(nmicf)]["ARM_CORTEX_A15"] = list()

            # Process tasks
            trace["micf_" + str(nmicf)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles = pc_micf_A7))
            trace["micf_" + str(nmicf)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles = pc_micf_A15))

            # write 1 token to channel
            for ncombwc in range(params.combwc):
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


        for ncombwc in range(params.combwc):
            trace["combwc_" + str(ncombwc)] = {}
            trace["combwc_" + str(ncombwc)]["ARM_CORTEX_A7"] = list()
            trace["combwc_" + str(ncombwc)]["ARM_CORTEX_A15"] = list()

            # read 1 token from channel
            for nmicf in range(params.micf):
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
            for nantcomb in range(params.antcomb):
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


        for nantcomb in range(params.antcomb):
            trace["antcomb_" + str(nantcomb)] = {}
            trace["antcomb_" + str(nantcomb)]["ARM_CORTEX_A7"] = list()
            trace["antcomb_" + str(nantcomb)]["ARM_CORTEX_A15"] = list()

            # read 1 token from channel
            for ncombwc in range(params.combwc):
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
            for nmicf in range(params.micf):
                trace["antcomb_" + str(nantcomb)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles=0, 
                write_to_channel="c_" + str(nantcomb) + "_" + str(nmicf + params.micf),
                n_tokens=1))
                trace["antcomb_" + str(nantcomb)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles=0, 
                write_to_channel="c_" + str(nantcomb) + "_" + str(nmicf + params.micf),
                n_tokens=1))

            # terminate
            trace["antcomb_" + str(nantcomb)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles=0, terminate=True))
            trace["antcomb_" + str(nantcomb)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles=0, terminate=True))

        for nmicf in range(params.micf):
            trace["micf_" + str(nmicf + params.micf)] = {}
            trace["micf_" + str(nmicf + params.micf)]["ARM_CORTEX_A7"] = list()
            trace["micf_" + str(nmicf + params.micf)]["ARM_CORTEX_A15"] = list()

            # read 1 token from channel
            for nantcomb in range(params.antcomb):
                trace["micf_" + str(nmicf + params.micf)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles=0, 
                read_from_channel="c_" + str(nantcomb) + "_" + str(nmicf + params.micf),
                n_tokens=1))
                trace["micf_" + str(nmicf + params.micf)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles=0, 
                read_from_channel="c_" + str(nantcomb) + "_" + str(nmicf + params.micf),
                n_tokens=1))

            # Process tasks
            trace["micf_" + str(nmicf + params.micf)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles = pc_micf_A7))
            trace["micf_" + str(nmicf + params.micf)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles = pc_micf_A15))

            # write 1 token to channel
            for ncombwc in range(params.combwc):
                trace["micf_" + str(nmicf + params.micf)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles=0, 
                write_to_channel="d_" + str(nmicf + params.micf) + "_" + str(ncombwc + params.combwc),
                n_tokens=1))
                trace["micf_" + str(nmicf + params.micf)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles=0, 
                write_to_channel="d_" + str(nmicf + params.micf) + "_" + str(ncombwc + params.combwc),
                n_tokens=1))

            # terminate
            trace["micf_" + str(nmicf + params.micf)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles=0, terminate=True))
            trace["micf_" + str(nmicf + params.micf)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles=0, terminate=True))

        for ncombwc in range(params.combwc):
            trace["combwc_" + str(ncombwc + params.combwc)] = {}
            trace["combwc_" + str(ncombwc + params.combwc)]["ARM_CORTEX_A7"] = list()
            trace["combwc_" + str(ncombwc + params.combwc)]["ARM_CORTEX_A15"] = list()

            # read 1 token from channel
            for nmicf in range(params.micf):
                trace["combwc_" + str(ncombwc + params.combwc)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles=0, 
                read_from_channel="d_" + str(nmicf + params.micf) + "_" + str(ncombwc + params.combwc),
                n_tokens=1))
                trace["combwc_" + str(ncombwc + params.combwc)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles=0, 
                read_from_channel="d_" + str(nmicf + params.micf) + "_" + str(ncombwc + params.combwc),
                n_tokens=1))

            # Process tasks
            trace["combwc_" + str(ncombwc + params.combwc)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles = pc_combwc_A7))
            trace["combwc_" + str(ncombwc + params.combwc)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles = pc_combwc_A15))

            # write 1 token to channel
            for nantcomb in range(params.antcomb):
                trace["combwc_" + str(ncombwc + params.combwc)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles=0, 
                write_to_channel="e_" + str(ncombwc + params.combwc) + "_" + str(nantcomb + params.antcomb),
                n_tokens=1))
                trace["combwc_" + str(ncombwc + params.combwc)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles=0, 
                write_to_channel="e_" + str(ncombwc + params.combwc) + "_" + str(nantcomb + params.antcomb),
                n_tokens=1))

            # terminate
            trace["combwc_" + str(ncombwc + params.combwc)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles=0, terminate=True))
            trace["combwc_" + str(ncombwc + params.combwc)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles=0, terminate=True))


        for nantcomb in range(params.antcomb):
            trace["antcomb_" + str(nantcomb + params.antcomb)] = {}
            trace["antcomb_" + str(nantcomb + params.antcomb)]["ARM_CORTEX_A7"] = list()
            trace["antcomb_" + str(nantcomb + params.antcomb)]["ARM_CORTEX_A15"] = list()

            # read 1 token from channel
            for ncombwc in range(params.combwc):
                trace["antcomb_" + str(nantcomb + params.antcomb)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles=0, 
                read_from_channel="e_" + str(ncombwc + params.combwc) + "_" + str(nantcomb + params.antcomb),
                n_tokens=1))
                trace["antcomb_" + str(nantcomb + params.antcomb)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles=0, 
                read_from_channel="e_" + str(ncombwc + params.combwc) + "_" + str(nantcomb + params.antcomb),
                n_tokens=1))

            # Process tasks
            trace["antcomb_" + str(nantcomb + params.antcomb)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles = pc_antcomb_A7))
            trace["antcomb_" + str(nantcomb + params.antcomb)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles = pc_antcomb_A15))

            # write 1 token to channel
            for ndemap in range(params.demap):
                trace["antcomb_" + str(nantcomb + params.antcomb)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles=0, 
                write_to_channel="f_" + str(nantcomb + params.antcomb) + "_" + str(ndemap),
                n_tokens=1))
                trace["antcomb_" + str(nantcomb + params.antcomb)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles=0, 
                write_to_channel="f_" + str(nantcomb + params.antcomb) + "_" + str(ndemap),
                n_tokens=1))

            # terminate
            trace["antcomb_" + str(nantcomb + params.antcomb)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles=0, terminate=True))
            trace["antcomb_" + str(nantcomb + params.antcomb)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles=0, terminate=True))

        for ndemap in range(params.demap):
            trace["demap_" + str(ndemap)] = {}
            trace["demap_" + str(ndemap)]["ARM_CORTEX_A7"] = list()
            trace["demap_" + str(ndemap)]["ARM_CORTEX_A15"] = list()

            # read 1 token from channel
            for nantcomb in range(params.antcomb):
                trace["demap_" + str(ndemap)]["ARM_CORTEX_A7"].\
                append(TraceSegment(process_cycles=0, 
                read_from_channel="f_" + str(nantcomb + params.antcomb) + "_" + str(ndemap),
                n_tokens=1))
                trace["demap_" + str(ndemap)]["ARM_CORTEX_A15"].\
                append(TraceSegment(process_cycles=0, 
                read_from_channel="f_" + str(nantcomb + params.antcomb) + "_" + str(ndemap),
                n_tokens=1))

            # Process tasks and terminate
            trace["demap_" + str(ndemap)]["ARM_CORTEX_A7"].\
            append(TraceSegment(process_cycles = pc_demap_A7, terminate=True))
            trace["demap_" + str(ndemap)]["ARM_CORTEX_A15"].\
            append(TraceSegment(process_cycles = pc_demap_A15, terminate=True))

        self.trace = trace

        # we also need to keep track of the current position in the trace
        self.trace_pos = {}

        for nmicf in range(params.micf*2):
            self.trace_pos["micf_" + str(nmicf)] = 0
        for ncombwc in range(params.combwc*2):
            self.trace_pos["combwc_" + str(ncombwc)] = 0
        for nantcomb in range(params.antcomb*2):
            self.trace_pos["antcomb_" + str(nantcomb)] = 0
        for ndemap in range(params.demap):
            self.trace_pos["demap_" + str(ndemap)] = 0

    def reset(self):
        self.trace_pos = {}
        for nmicf in range(params.micf*2):
            self.trace_pos["micf_" + str(nmicf)] = 0
        for ncombwc in range(params.combwc*2):
            self.trace_pos["combwc_" + str(ncombwc)] = 0
        for nantcomb in range(params.antcomb*2):
            self.trace_pos["antcomb_" + str(nantcomb)] = 0
        for ndemap in range(params.demap):
            self.trace_pos["demap_" + str(ndemap)] = 0

    def next_segment(self, process_name, processor_type):
        pos = self.trace_pos[process_name]
        self.trace_pos[process_name] = pos + 1
        return self.trace[process_name][processor_type][pos]


class FiveGSimulation(BaseSimulation):
    """Simulate the processing of 5G data"""

    def __init__(self, platform):
        super().__init__(platform)

    @staticmethod
    def from_hydra(cfg):
        platform = hydra.utils.instantiate(cfg['platform'])
        return FiveGSimulation(platform)

    def _manager_process(self):
        trace_writer = self.system.trace_writer

        app_finished = []

        i = 0
        # while end of file not reached:
        while params.TFM.TF_EOF is not True:
            
            params.nsubframe = params.TFM.get_next_subframe()
            
            # run 100 instances of the 5G app, start one every 1 ms
            for ntrace in params.nsubframe.trace:
                # create a new graph and trace
                params.ntrace = ntrace
                
                params.micf = PHY.get_num_micf( ntrace.layers)
                params.combwc = PHY.get_num_combwc()
                params.antcomb = PHY.get_num_antcomb(ntrace.layers)
                params.demap = PHY.get_num_demap()
    
                kpn = FivegGraph()
                trace = FivegTraceGenerator()
    
                # create a new mapper (this should be TETRiS in the future) Note
                # that we need to create a new mapper here, as the KPN could change
                # This appears to be a weakness of our mapper interface. The KPN
                # should probably become a parameter of generate_mapping().
                cfg = {'random_seed': None}
                mapper = RandomMapper(kpn, self.platform, cfg)
                # create a new mapping
                mapping = mapper.generate_mapping()
                # instantiate the application
                app = RuntimeKpnApplication(name=f"fiveg{i:06}",
                                            kpn_graph=kpn,
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
                
                i += 1
                
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


class HydraFiveGSimulation(FiveGSimulation):
    """Required to instatiate a FiveGSimulation from hydra<1.0"""
    def __new__(cls, cfg):
        return FiveGSimulation.from_hydra(cfg)
