import hydra

from pykpn.mapper.random import RandomMapper
from pykpn.common.kpn import KpnGraph, KpnProcess, KpnChannel
from pykpn.common.trace import TraceGenerator, TraceSegment
from pykpn.simulate import BaseSimulation
from pykpn.simulate.application import RuntimeKpnApplication


class DummyGraph(KpnGraph):
    """The KPN graph of a dummy application

    This is intended to be refined into a 5G graph.

    The dummy graph consists of three tasks:
    source -> compute -> sink

    For the final 5G graph it probably makes sense to parameterize this class
    and build slightly different graphs for different parts in the 5G trace.
    """

    def __init__(self):
        super().__init__("dummy")
        # 3 processes
        source = KpnProcess("source")
        compute = KpnProcess("compute")
        sink = KpnProcess("sink")
        # and 2 channels (with a token size of 16 bytes each)
        chan_src = KpnChannel("chan_src", 16)
        chan_sink = KpnChannel("chan_sink", 16)
        # connect the processes
        source.connect_to_outgoing_channel(chan_src)
        compute.connect_to_incomming_channel(chan_src)
        compute.connect_to_outgoing_channel(chan_sink)
        sink.connect_to_incomming_channel(chan_sink)
        # register all processes and channels
        self.add_process(source)
        self.add_process(compute)
        self.add_process(sink)
        self.add_channel(chan_src)
        self.add_channel(chan_sink)


class DummyTraceGenerator(TraceGenerator):
    """Generates traces for the dummy application

    This is a bit clumsy to do by hand at the moment. We might improve this in
    the near future.
    """

    def __init__(self):
        # build a dictionary of all the traces
        trace = {}

        # trace for process source on core type ARM_CORTEX_A7
        trace["source"] = {}
        trace["source"]["ARM_CORTEX_A7"] = [
            # Process 1500 cycles, then write 1 token to chan_src, and
            # terminate
            TraceSegment(process_cycles=1500, write_to_channel="chan_src",
                         n_tokens=1, terminate=True)
        ]
        # trace for process source on core type ARM_CORTEX_A15
        trace["source"]["ARM_CORTEX_A15"] = [
            # Process 1000 cycles, then write 1 token to chan_src, and
            # terminate
            TraceSegment(process_cycles=1000, write_to_channel="chan_src",
                         n_tokens=1, terminate=True)
        ]

        # trace for process compute on core type ARM_CORTEX_A7
        trace["compute"] = {}
        trace["compute"]["ARM_CORTEX_A7"] = [
            # Read one token from channel chan_src
            TraceSegment(process_cycles=0, read_from_channel="chan_src",
                         n_tokens=1),
            # Process 15,000,000 cycles, then write 1 token to chan_sink, and
            # terminate
            TraceSegment(process_cycles=15000000,
                         write_to_channel="chan_sink", n_tokens=1,
                         terminate=True)
        ]
        # trace for process compute on core type ARM_CORTEX_A15
        trace["compute"]["ARM_CORTEX_A15"] = [
            # Read one token from channel chan_src
            TraceSegment(process_cycles=0, read_from_channel="chan_src",
                         n_tokens=1),
            # Process 10,000,000 cycles, then write 1 token to chan_sink, and
            # terminate
            TraceSegment(process_cycles=10000000,
                         write_to_channel="chan_sink", n_tokens=1,
                         terminate=True)
        ]

        # trace for process source on core type ARM_CORTEX_A7
        trace["sink"] = {}
        trace["sink"]["ARM_CORTEX_A7"] = [
            # Read one token from channel chan_sink
            TraceSegment(process_cycles=0, read_from_channel="chan_sink",
                         n_tokens=1),
            # Process 1500 cycles, then terminate
            TraceSegment(process_cycles=1500, terminate=True)
        ]
        # trace for process source on core type ARM_CORTEX_A15
        trace["sink"]["ARM_CORTEX_A15"] = [
            # Read one token from channel chan_sink
            TraceSegment(process_cycles=0, read_from_channel="chan_sink",
                         n_tokens=1),
            # Process 1000 cycles, then terminate
            TraceSegment(process_cycles=1000, terminate=True)
        ]

        self.trace = trace

        # we also need to keep track of the current position in the trace
        self.trace_pos = {"source": 0, "compute": 0, "sink": 0}

    def reset(self):
        self.trace_pos = {"source": 0, "compute": 0, "sink": 0}

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
        app_finished = []
        # run 10 instances of the dummy app, start one every 5 ms
        for i in range(0, 10):
            # create a new graph and trace
            kpn = DummyGraph()
            trace = DummyTraceGenerator()
            # create a new mapper (this should be TETRiS in the future) Note
            # that we need to create a new mapper here, as the KPN could change
            # This appears to be a weakness of our mapper interface. The KPN
            # should probably become a parameter of generate_mapping().
            cfg = {'random_seed': None}
            mapper = RandomMapper(kpn, self.platform, cfg)
            # create a new mapping
            mapping = mapper.generate_mapping()
            # instantiate the application
            app = RuntimeKpnApplication(name=f"dummy{i}",
                                        kpn_graph=kpn,
                                        mapping=mapping,
                                        trace_generator=trace,
                                        system=self.system)
            # start the application
            finished = self.env.process(app.run())
            app_finished.append(finished)
            # wait for 5 ms
            yield self.env.timeout(5000000000)

        # wait until all applications finished
        yield self.env.all_of(app_finished)

    def run(self):
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
