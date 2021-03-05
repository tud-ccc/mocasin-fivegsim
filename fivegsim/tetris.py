# Copyright (C) 2021 TU Dresden
# All Rights Reserved
#
# Authors: Robert Khasanov, Christian Menard

from fivegsim.fiveg_mapper import FiveGParetoFrontCache
from fivegsim.simulation import FiveGRuntimeDataflowApplication
from mocasin.simulate.tetris import RuntimeTetrisManager


class FiveGRuntimeTetrisManager(RuntimeTetrisManager):
    def __init__(self, resource_manager, system, cfg, stats=None):
        """Tetris Manager for FiveG applications."""
        super().__init__(resource_manager, system)
        self.pareto_cache = FiveGParetoFrontCache(self.system.platform, cfg)
        self.stats = stats

    def _update_statistics(self):
        """Update statistics structure.

        Update the expected end time of the applications. The method should be
        called after new schedule is generated.
        """
        if not self.stats:
            return
        schedule = self.resource_manager.schedule
        # Update accepted tasks
        if schedule:
            for request, segments in schedule.per_requests().items():
                assert segments[-1].finished
                expected_end_time = segments[-1].end_time
                entry = self.stats.find(request.app)
                assert entry
                # Put the stats entry to runtime application
                # TODO: This is an ad-hoc, need to rethink the design
                if entry.accepted is None:
                    runtime_app = self._runtime_applications[request]
                    assert runtime_app.is_new()
                    runtime_app.stats_entry = entry
                entry.accepted = True
                entry.expected_end_time = expected_end_time * 1000000000.0
        # mark all other stats as rejected
        for entry in self.stats.entries():
            if entry.accepted is None:
                entry.accepted = False

    def start_applications(self, graphs, traces):
        """Start new applications."""
        pareto_fronts = []
        timeouts = []
        for graph, trace in zip(graphs, traces):
            # Generate Pareto-optimal mappings
            pareto_front = self.pareto_cache.get_pareto_front(graph, trace)
            pareto_fronts.append(pareto_front)
            timeouts.append(graph.timeout / 1000000000.0)
        super().start_applications(graphs, traces, pareto_fronts, timeouts)

    def _generate_schedule(self):
        # initialize statistics
        if self.stats:
            for graph, _, _, _ in self._new_applications:
                deadline = self.env.now + graph.timeout
                self.stats.create_entry(
                    graph, arrival=self.env.now, deadline=deadline
                )
        # Call the base method
        super()._generate_schedule()
        # update the statistics
        self._update_statistics()

    def _create_runtime_application(self, request, trace):
        graph = request.app
        deadline = request.deadline * 1000000000.0
        return FiveGRuntimeDataflowApplication(
            name=graph.name,
            graph=graph,
            app_trace=trace,
            system=self.system,
            deadline=deadline,
        )
