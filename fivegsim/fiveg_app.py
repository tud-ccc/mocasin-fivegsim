# Copyright (C) 2020 TU Dresden
# All Rights Reserved
#
# Authors: Julian Robledo, Christian Menard

from fivegsim.fiveg_graph import FivegGraph

from mocasin.simulate.application import RuntimeDataflowApplication


class FiveGRuntimeDataflowApplication(RuntimeDataflowApplication):
    """Represents the runtime instance of the 5g application.

    Args:
        name (str): the application name
        graph (FivegGraph): the graph denoting the dataflow application
        mapping (Mapping): a mapping to the platform implemented by system
        app_trace (FivegTrace): the trace representing the execution
            behavior of the application
        system (System): the system the application is supposed to be
            executed on
        deadline (int): the absolute deadline if specified, otherwise it is
            calculated from the application criticality
        stats_entry (SimulationStatisticsEntry): the statistics entry of
            the application
    """

    def __init__(
        self, name, graph, app_trace, system, deadline=None, stats_entry=None
    ):

        super().__init__(name, graph, app_trace, system)

        assert isinstance(graph, FivegGraph)
        self.criticality = graph.criticality
        self.prbs = graph.prbs
        self.mod = graph.mod
        self.deadline = deadline
        self.stats_entry = stats_entry

    def run(self, mapping):
        """Start execution of this application

        Yields:
            ~simpy.events.Event: an event that is triggered when the
                application finishes execution.
        """
        miss = 0

        self._log.info(f"Application {self.name} starts")

        # record application start in the simulation trace
        self.system.trace_writer.begin_duration(
            "instances", self.name, self.name
        )

        # record start time
        start = self.env.now

        # calculate the deadline
        if not self.deadline:
            timeout = self.graph.timeout
            self.deadline = start + timeout
        timeout = self.deadline - start
        assert timeout > 0

        # start the application
        finished = self.env.process(super().run(mapping))
        # wait until the application finished or we reach the timeout
        yield self.env.any_of([finished, self.env.timeout(timeout)])
        # record termination time
        end = self.env.now
        # kill the application if it is not finished (we reached the timeout)
        if not finished.processed:
            self.kill()
            miss = 1

        # record application termination in the simulation trace
        self.system.trace_writer.end_duration("instances", self.name, self.name)

        # save stats
        if self.stats_entry:
            self.stats_entry.start_time = start
            self.stats_entry.end_time = end
            self.stats_entry.deadline_miss = miss
