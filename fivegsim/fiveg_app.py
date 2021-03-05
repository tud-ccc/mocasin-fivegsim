# Copyright (C) 2020 TU Dresden
# All Rights Reserved
#
# Authors: Julian Robledo, Christian Menard

from fivegsim.fiveg_graph import FivegGraph

from mocasin.simulate.application import RuntimeDataflowApplication

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

        # record start time
        start = self.env.now
        # start the application
        finished = self.env.process(super().run())
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
        with open("stats.csv", "a") as stats_file:
            stats_file.write(
                f"{start},{end},{self.criticality},{miss},{self.prbs},"
                f"{self.mod}\n"
            )
