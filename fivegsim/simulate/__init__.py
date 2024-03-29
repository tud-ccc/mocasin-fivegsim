# Copyright (C) 2020 TU Dresden
# Licensed under the ISC license (see LICENSE.txt)
#
# Authors: Julian Robledo, Christian Menard

import copy
import csv
import logging
import sys

import hydra

from mocasin.common.graph import DataflowGraph
from mocasin.common.mapping import Mapping
from mocasin.common.trace import (
    DataflowTrace,
    SegmentType,
)
from mocasin.simulate import BaseSimulation, SimulationResult
from mocasin.simulate import scheduler
from mocasin.tetris.manager import ResourceManager

from fivegsim.graph import FivegGraph
from fivegsim.simulate.application import FiveGRuntimeDataflowApplication
from fivegsim.simulate.load_balancer import PhybenchLoadBalancer
from fivegsim.simulate.statistics import FiveGManagerStatistics
from fivegsim.simulate.tetris import FiveGRuntimeTetrisManager
from fivegsim.trace import FivegTrace
from fivegsim.util.proc_tgff_reader import get_task_time
from fivegsim.util.trace_file_manager import TraceFileManager

sys.setrecursionlimit(10000)

# increase queue len that is used for load calculations
scheduler._MAX_DEQUE_LEN = 5000

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
    """Simulate the processing of 5G data."""

    def __init__(self, platform, cfg, trace_file, task_file, **kwargs):
        super().__init__(platform)
        self.cfg = cfg
        self.num_antennas = self.cfg["antennas"]

        # Get lte traces
        self.TFM = TraceFileManager(hydra.utils.to_absolute_path(trace_file))
        self.ntrace = TraceFileManager.Trace()

        # Get task execution time info
        self.proc_time = get_task_time(hydra.utils.to_absolute_path(task_file))

        # a list of application started during execution
        self.app_finished = []

        # initialize simulation statistics
        self.stats = FiveGManagerStatistics()

    @staticmethod
    def from_hydra(cfg, **kwargs):
        platform = hydra.utils.instantiate(cfg["platform"])
        return FiveGSimulation(platform, cfg, **kwargs)

    def _generate_graphs(self, sf_id, nsubframe):
        graphs = []
        i = 0
        for ntrace in nsubframe.trace:
            # create a new graph
            graphs.append(
                FivegGraph(f"fiveg_sf{sf_id}_{i}", ntrace, self.num_antennas)
            )
            i += 1
        return graphs

    def _generate_traces(self, nsubframe):
        traces = []
        for ntrace in nsubframe.trace:
            # create a new graph
            traces.append(FivegTrace(ntrace, self.proc_time, self.num_antennas))
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
        mapper = hydra.utils.instantiate(self.cfg["mapper"], self.platform)
        # create a mapping for the entire subframe
        sf_mapping = mapper.generate_mapping(
            sf_graph, trace=sf_trace, representation=rep
        )
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
            graph = mapping.graph
            # create a statistics entry for the application
            deadline = self.env.now + graph.timeout
            stats_entry = self.stats.new_application(
                graph, arrival=self.env.now, deadline=deadline
            )
            # FIXME: There should be a way to set this when creating the entry
            # (or make true the default value)
            stats_entry.accepted = True
            # instantiate the application
            app = FiveGRuntimeDataflowApplication(
                name=graph.name,
                graph=graph,
                app_trace=trace,
                system=self.system,
                deadline=deadline,
                stats_entry=stats_entry,
            )
            # start the application
            finished = self.env.process(app.run(mapping))
            # keep the finished event for later
            self.app_finished.append(finished)

    def _process_5g_subframes(self):
        """Process 5g subframes.

        Iterate over all subframes found in the 5g trace and simulate their
        processing.
        """
        sf_count = 0

        runtime = None
        assert not (self.cfg["load_balancer"] and self.cfg["tetris_runtime"])

        # start load balancer runtime if needed
        if self.cfg["load_balancer"]:
            runtime = PhybenchLoadBalancer(self.system, self.cfg, self.stats)
            finished = self.env.process(runtime.run())
            self.app_finished = [finished]
            # make sure the startup of the runtime is processed completely
            yield self.env.timeout(0)

        # start tetris runtime if needed
        if self.cfg["tetris_runtime"]:
            scheduler = hydra.utils.instantiate(
                self.cfg["resource_manager"], self.platform
            )
            resource_manager = ResourceManager(
                self.platform,
                scheduler,
                schedule_iteratively=self.cfg["tetris_iterative"],
            )
            runtime = FiveGRuntimeTetrisManager(
                resource_manager, self.system, self.cfg, self.stats
            )
            finished = self.env.process(runtime.run())
            self.app_finished = [finished]

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

            if runtime:
                # let the runtime handle the applications
                runtime.start_applications(graphs, traces)
            else:
                # if there is no runtime, we directly create mappings and start
                # the applications

                # generate mappings
                mappings = self._generate_mappings(
                    f"sf_{sf_count}", graphs, traces
                )

                # simulate the application execution
                log.info(f"start applications for subframe {sf_count}")
                self._start_applications(mappings, traces, nsubframe)

            # wait for 1 ms
            yield self.env.timeout(1000000000)

        # if we use the runtime manager, we let it know that applications
        # for all subframes where started and it can shutdown as soon as all
        # the applications finish
        if runtime:
            runtime.shutdown()

        # wait until all applications finished
        yield self.env.all_of(self.app_finished)

        stats = self.stats
        print(f"Total applications: {stats.total_applications()}")
        print(f"Total rejected: {stats.total_rejected()}")
        print(f"Missed deadline: {stats.total_missed()}")
        print(f"Total runtime manager activations: {stats.total_activations()}")
        st_mean, st_std = stats.scheduling_time_stats()
        print(
            f"Average scheduling time: {st_mean * 1000:.6f} ms "
            f"(std={st_std * 1000:.6f} ms)"
        )
        stats.dump_activations(self.cfg["stats_activations"])
        stats.dump_applications(self.cfg["stats_applications"])
        self.to_file(stats)

    def _run(self):
        """Run the simulation.

        May only be called once. Updates the :attr:`results` attribute.
        """
        if self.result is not None:
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
        self.result = SimulationResult(
            exec_time=self.env.now, static_energy=None, dynamic_energy=None
        )
        energy = self.system.calculate_energy()
        # If the power model is enabled, also save the energy consumption
        if energy:
            static_energy, dynamic_energy = energy
            self.result.static_energy = static_energy
            self.result.dynamic_energy = dynamic_energy

    def to_file(self, stats):
        stats_dict = {}
        stats_dict["Total_apps"] = str(stats.total_applications())
        stats_dict["Total_rejected"] = str(stats.total_rejected())
        stats_dict["Missed_deadline"] = str(stats.total_missed())
        stats_dict["Total_activations"] = str(stats.total_activations())
        stats_dict["Total_scheduling_time"] = str(stats.total_scheduling_time())
        st_mean, st_std = stats.scheduling_time_stats()
        stats_dict["Average_scheduling_time"] = str(st_mean)
        stats_dict["Std_scheduling_time"] = str(st_std)
        with open("missrate.csv", "x") as file:
            writer = csv.writer(
                file,
                delimiter=",",
                lineterminator="\n",
            )
            writer.writerow(stats_dict.keys())
            writer.writerow(stats_dict.values())
