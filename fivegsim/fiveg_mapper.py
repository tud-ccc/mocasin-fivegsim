# Copyright (C) 2021 TU Dresden
# All Rights Reserved
#
# Authors: Robert Khasanov

"""This is a placeholder for FiveGMapper, which will be implemented soon."""

from copy import copy

import hydra

from mocasin.mapper.fair import StaticCFSMapper
from mocasin.mapper.utils import SimulationManager


class FiveGParetoFrontCache:
    def __init__(self, platform, cfg):
        self.platform = platform
        self.cfg = cfg
        self._cache = {}

    def _get_graph_invariant(self, graph):
        """Get the internal graph invariant based on its properies."""
        return f"fiveg_prbs{graph.prbs}_mod{graph.mod}_lay{graph.layers}"

    # FIXME: remove the trace
    def get_pareto_front(self, graph, trace):
        invariant = self._get_graph_invariant(graph)
        if invariant in self._cache:
            pareto_front = []
            for mapping in self._cache[invariant]:
                new_mapping = copy(mapping)
                new_mapping.graph = graph
                pareto_front.append(new_mapping)
            return pareto_front
        # TODO: Change to FiveGMapper
        rep = hydra.utils.instantiate(
            self.cfg["representation"], graph, self.platform
        )
        mapper = StaticCFSMapper(graph, self.platform, trace, rep)
        pareto_front = mapper.generate_pareto_front()
        simulation_manager = SimulationManager(
            rep, trace, jobs=None, parallel=True
        )
        simulation_manager.simulate(pareto_front)
        for mapping in pareto_front:
            simulation_manager.append_mapping_metadata(mapping)
        self._cache[invariant] = pareto_front
        return pareto_front


class FiveGMapper:
    """FiveG-specific mapper.

    This mapper is a load balancing mapper which takes into account
    the specifics of baseband processing flow. The application has four phases,
    each phase is implemented with data-level parallelism and consists of one to
    four tasks.

    Processes in the single phase processing the same data are considered as one
    process (as they were fused). The processes in the single phase processing
    the different portion of the input are distributed among all available cores
    in balanced fashion.
    """

    pass
