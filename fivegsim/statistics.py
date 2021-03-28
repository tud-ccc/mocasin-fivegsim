# Copyright (C) 2021 TU Dresden
# All Rights Reserved
#
# Author: Robert Khasanov

import csv
from dataclasses import asdict, dataclass

from fivegsim.fiveg_graph import FivegGraph


@dataclass
class SimulationStatisticsEntry:
    """A single entry for the application statistics."""

    graph: FivegGraph
    arrival: int
    deadline: int

    # Tetris-specific
    accepted: bool = None
    expected_end_time: float = None

    start_time: int = None
    end_time: int = None
    deadline_miss: bool = None

    def to_dict(self):
        d = asdict(self)
        del d["graph"]
        d["name"] = self.graph.name
        d["prbs"] = self.graph.prbs
        d["mod"] = self.graph.mod
        d["criticality"] = self.graph.criticality
        return d


class SimulationStatistics:
    """Collection and export of statistics after simulation."""

    def __init__(self, using_tetris=False):
        self._entries = []
        self._using_tetris = using_tetris

    def create_entry(self, graph, arrival=None, deadline=None):
        if not isinstance(graph, FivegGraph):
            raise RuntimeError("Incompatible type of the graph")
        entry = SimulationStatisticsEntry(
            graph=graph, arrival=arrival, deadline=deadline
        )
        self._entries.append(entry)
        return entry

    def length(self):
        """Returns the total number of entries."""
        return len(self._entries)

    def total_accepted(self):
        """Returns the number of accepted applications."""
        if self._using_tetris:
            return len([x for x in self._entries if x.accepted])
        else:
            return self.length()

    def total_rejected(self):
        """Returns the number of rejected applications."""
        return self.length() - self.total_accepted()

    def total_missed(self):
        """Returns the number of applications missed the deadline."""
        return len([x for x in self._entries if x.deadline_miss])

    def find(self, graph):
        """Find the entry by the graph object."""
        for entry in self._entries:
            if entry.graph == graph:
                return entry
        return None

    def dump(self, filename):
        fieldnames = [
            "name",
            "arrival",
            "prbs",
            "mod",
            "criticality",
            "deadline",
            "accepted",
            "expected_end_time",
            "start_time",
            "end_time",
            "deadline_miss",
        ]
        with open(filename, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for entry in self._entries:
                writer.writerow(entry.to_dict())
