# Copyright (C) 2021 TU Dresden
# Licensed under the ISC license (see LICENSE.txt)
#
# Authors: Robert Khasanov

import hydra

from mocasin.mapper.partial import (
    ComFullMapper,
    ProcPartialMapper,
)
from mocasin.mapper.utils import SimulationManager


class FiveGParetoFrontCache:
    """FiveG Pareto-Front Cache."""

    def __init__(self, platform, cfg):
        self.platform = platform
        self.cfg = cfg
        self.pareto_metadata_simulate = cfg["pareto_metadata_simulate"]
        self.pareto_time_scale = cfg["pareto_time_scale"] * 1.0
        self.pareto_time_offset = cfg["pareto_time_offset"] * 1.0
        self._cache = {}

        assert isinstance(self.pareto_metadata_simulate, bool)
        assert isinstance(self.pareto_time_scale, float)
        assert isinstance(self.pareto_time_offset, float)

    def _get_graph_invariant(self, graph):
        """Get the internal graph invariant based on its properies."""
        return f"fiveg_prbs{graph.prbs}_mod{graph.mod}_lay{graph.layers}"

    def get_pareto_front(self, graph, trace):
        """Get Pareto-Front for a given graph and trace."""
        invariant = self._get_graph_invariant(graph)
        if invariant in self._cache:
            pareto_front = self._to_mappings(graph, self._cache[invariant])
        else:
            pareto_front = self._generate_pareto_front(graph, trace)
            self._cache[invariant] = self._to_lists(pareto_front)
        return pareto_front

    def _to_lists(self, pareto_mappings):
        res = []
        for mapping in pareto_mappings:
            res.append((mapping.to_list(), mapping.metadata))
        return res

    def _to_mappings(self, graph, pareto_lists):
        com_mapper = ComFullMapper(graph, self.platform)
        mapper = ProcPartialMapper(graph, self.platform, com_mapper)
        res = []
        for mapping_list, metadata in pareto_lists:
            mapping = mapper.generate_mapping(mapping_list)
            mapping.metadata.exec_time = metadata.exec_time
            mapping.metadata.energy = metadata.energy
            res.append(mapping)
        return res

    # FIXME: remove the trace
    def _generate_pareto_front(self, graph, trace):
        rep = hydra.utils.instantiate(
            self.cfg["representation"], graph, self.platform
        )
        mapper = hydra.utils.instantiate(
            self.cfg["mapper"], graph, self.platform, trace, rep
        )
        pareto_front = mapper.generate_pareto_front()

        # estimate time and energy by simulation
        if self.pareto_metadata_simulate:
            simulation_manager = SimulationManager(
                rep, trace, jobs=None, parallel=True
            )
            simulation_manager.simulate(pareto_front)
            for mapping in pareto_front:
                simulation_manager.append_mapping_metadata(mapping)

        # rescale execution time
        for mapping in pareto_front:
            mapping.metadata.exec_time = (
                mapping.metadata.exec_time * self.pareto_time_scale
                + self.pareto_time_offset
            )

        return pareto_front
