# Copyright (C) 2021 TU Dresden
# All Rights Reserved
#
# Author: Robert Khasanov

from dataclasses import dataclass

from mocasin.simulate.manager import (
    ManagerStatistics,
    ManagerStatisticsApplicationEntry,
)


@dataclass
class FiveGManagerStatisticsApplicationEntry(ManagerStatisticsApplicationEntry):
    """A log entry of the application scheduling with the runtime manager."""

    prbs: int
    mod: int
    criticality: int


class FiveGManagerStatistics(ManagerStatistics):
    """Collection and export of statistics after simulation."""

    def new_application(self, graph, arrival=None, deadline=None):
        """Create an application entry."""
        entry = FiveGManagerStatisticsApplicationEntry(
            name=graph.name,
            prbs=graph.prbs,
            mod=graph.mod,
            criticality=graph.criticality,
            arrival=arrival,
            deadline=deadline,
        )
        self.applications[entry.name] = entry
        return entry
