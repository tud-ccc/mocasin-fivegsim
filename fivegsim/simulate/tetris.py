# Copyright (C) 2021 TU Dresden
# All Rights Reserved
#
# Authors: Robert Khasanov, Christian Menard

from mocasin.simulate.tetris import RuntimeTetrisManager

from fivegsim.mapper.pareto import FiveGParetoFrontCache
from fivegsim.simulate import FiveGRuntimeDataflowApplication


class FiveGRuntimeTetrisManager(RuntimeTetrisManager):
    def __init__(self, resource_manager, system, cfg, stats=None):
        """Tetris Manager for FiveG applications."""
        super().__init__(resource_manager, system, stats)
        self.pareto_cache = FiveGParetoFrontCache(self.system.platform, cfg)

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

    def _create_runtime_application(self, request, trace):
        graph = request.app
        deadline = request.deadline * 1000000000.0
        stats_entry = self.statistics.find_application(graph.name)
        app = FiveGRuntimeDataflowApplication(
            name=graph.name,
            graph=graph,
            app_trace=trace,
            system=self.system,
            deadline=deadline,
            stats_entry=stats_entry,
        )
        return app
