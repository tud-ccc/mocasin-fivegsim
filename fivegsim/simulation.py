# Copyright (C) 2020 TU Dresden
# All Rights Reserved
#
# Authors: Julian Robledo, Christian Menard

import copy
import logging
import hydra
import sys

from mocasin.common.graph import DataflowGraph
from mocasin.common.mapping import Mapping
from mocasin.common.trace import (
    DataflowTrace,
    SegmentType,
)
from mocasin.simulate import BaseSimulation
from mocasin.simulate.application import RuntimeDataflowApplication

from fivegsim.trace_file_manager import TraceFileManager
from fivegsim.proc_tgff_reader import get_task_time
from fivegsim.fiveg_graph import FivegGraph
from fivegsim.fiveg_trace import FivegTrace

sys.setrecursionlimit(10000)

log = logging.getLogger(__name__)


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

        # a list of application started during execution
        self.app_finished = []

    @staticmethod
    def from_hydra(cfg, **kwargs):
        platform = hydra.utils.instantiate(cfg["platform"])
        return FiveGSimulation(platform, cfg, **kwargs)

    def _generate_graphs(self, sf_id, nsubframe):
        graphs = []
        i = 0
        for ntrace in nsubframe.trace:
            # create a new graph
            graphs.append(FivegGraph(f"fiveg_sf{sf_id}_{i}", ntrace))
            i += 1
        return graphs

    def _generate_traces(self, nsubframe):
        traces = []
        for ntrace in nsubframe.trace:
            # create a new graph
            traces.append(FivegTrace(ntrace, self.proc_time))
        return traces

    def _merge_graphs_and_traces(self, app_name, graphs, traces):
        # create a combined graph
        sf_graph = DataflowGraph(app_name)
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

        return sf_graph, sf_trace

    def _generate_mappings(self, sf_name, graphs, traces):
        # XXX Merge the applications and traces given above into one large
        # graph and trace for the entire subframe. This is just a workaround
        # for our mapper API that only accepts a single mapping
        sf_graph, sf_trace = self._merge_graphs_and_traces(
            sf_name, graphs, traces
        )

        # create a new mapper (this should be TETRiS in the future) Note
        # that we need to create a new mapper here, as the GRAPH could change
        # This appears to be a weakness of our mapper interface. The GRAPH
        # should probably become a parameter of generate_mapping().
        log.info(f"generate mapping for {sf_name}")
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
        log.info("mapping generation done")

        # Split the mapping up again. We merged all graphs and traces
        # into a single graph and trace and generated a mapping for this big
        # combined application. Now we need to extract "submappings" for the
        # individual graphs.
        mappings = []
        for graph in graphs:
            mapping = Mapping(graph, self.platform)
            for sf_p in sf_mapping._process_info.keys():
                if sf_p.startswith(graph.name):
                    p = sf_p[len(graph.name) + 1 :]
                    mapping._process_info[p] = sf_mapping._process_info[sf_p]
            for sf_c in sf_mapping._channel_info.keys():
                if sf_c.startswith(graph.name):
                    c = sf_c[len(graph.name) + 1 :]
                    mapping._channel_info[c] = sf_mapping._channel_info[sf_c]
            mappings.append(mapping)

        return mappings

    def _start_applications(self, mappings, traces, nsubframe):
        for mapping, trace in zip(mappings, traces):
            # instantiate the application
            app = FiveGRuntimeDataflowApplication(
                name=mapping.graph.name,
                graph=mapping.graph,
                mapping=mapping,
                app_trace=trace,
                system=self.system,
            )
            # start the application
            finished = self.env.process(app.run())
            # keep the finished event for later
            self.app_finished.append(finished)

    def _process_5g_subframes(self):
        """Iterate over all subframes found in the 5g trace and simulate their
        processing.
        """
        sf_count = 0

        with open("stats.csv", "w") as stats_file:
            stats_file.write("startTime,endTime,criticality,miss,prbs,mod\n")

        # while end of file not reached:
        while self.TFM.TF_EOF is not True:
            # get next subframe
            nsubframe = self.TFM.get_next_subframe()

            # generate graphs and traces for current subframe
            graphs = self._generate_graphs(sf_count, nsubframe)
            traces = self._generate_traces(nsubframe)
            sf_count += 1

            # just wait and try again if there is nothing to process
            if len(graphs) == 0:
                # wait for 1 ms
                yield self.env.timeout(1000000000)
                continue

            # generate mappings
            mappings = self._generate_mappings(f"sf_{sf_count}", graphs, traces)

            # simulate the application execution
            log.info(f"start applications for subframe {sf_count}")
            self._start_applications(mappings, traces, nsubframe)

            # wait for 1 ms
            yield self.env.timeout(1000000000)

        # wait until all applications finished
        yield self.env.all_of(self.app_finished)

        print("missrate = " + str(self.get_missrate()))

    def _run(self):
        """Run the simulation.

        May only be called once. Updates the :attr:`exec_time` attribute.
        """
        if self.exec_time is not None:
            raise RuntimeError("A FiveGSimulation may only be run once!")

        # start all schedulers
        self.system.start_schedulers()
        # start the f process
        finished = self.env.process(self._process_5g_subframes())
        # run the actual simulation until the manager process finishes
        self.env.run(finished)
        # check if all graph processes finished execution
        self.system.check_errors()
        # save the execution time
        self.exec_time = self.env.now

    def get_missrate(self):
        with open("stats.csv", "r") as stats_file:
            lines = stats_file.readlines()  # Load all lines
        lines.pop(0)  # Remove first line
        lines = [x.strip() for x in lines]
        lines = [x.split(",") for x in lines]
        num_miss = 0
        for line in lines:
            num_miss += int(line[3])
        return num_miss / len(lines)


class FiveGRuntimeDataflowApplication(RuntimeDataflowApplication):
    def __init__(self, name, graph, mapping, app_trace, system):
        super().__init__(name, graph, mapping, app_trace, system)

        assert isinstance(graph, FivegGraph)
        self.criticality = graph.criticality
        self.prbs = graph.prbs
        self.mod = graph.mod

    def run(self):
        """Start execution of this application

        Yields:
            ~simpy.events.Event: an event that is triggered when the
                application finishes execution.
        """
        miss = 0

        if self.criticality == 0:
            timeout = 2500000000
        elif self.criticality == 1:
            timeout = 500000000
        elif self.criticality == 2:
            timeout = 2500000000
        else:
            raise ValueError("Unknown criticality")

        self._log.info(f"Application {self.name} starts")

        # record application start in the simulation trace
        self.system.trace_writer.begin_duration(
            "instances", self.name, self.name
        )

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

        # record application termination in the simulation trace
        self.system.trace_writer.end_duration("instances", self.name, self.name)

        # save stats
        with open("stats.csv", "a") as stats_file:
            stats_file.write(
                f"{start},{end},{self.criticality},{miss},{self.prbs},"
                f"{self.mod}\n"
            )
