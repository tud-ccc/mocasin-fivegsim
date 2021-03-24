# Copyright (C) 2021 TU Dresden
# All Rights Reserved
#
# Authors: Robert Khasanov, Christian Menard

import hydra
import logging

from mocasin.mapper.random import RandomMapper
from mocasin.simulate.adapter import SimulateLoggerAdapter

from fivegsim.simulation import FiveGRuntimeDataflowApplication

log = logging.getLogger(__name__)


class PhybenchLoadBalancer:
    def __init__(self, system, cfg):
        self.system = system
        self.cfg = cfg

        # keep track of all running applications
        self._running_applications = {}

        # a special logger that allows printing timestamped messages
        self._log = SimulateLoggerAdapter(log, "Load Balancer", self.env)

        # an event indicating that the runtime should shut down
        self._request_shutdown = self.env.event()

        # a list to keep track of all events indicating when an app finished
        self._finished_events = []

    def run(self):
        """A simpy process modelling the actual runtime."""

        self._log.info("Starting up")

        yield self._request_shutdown

        # wait for all applications to terminate
        yield self.env.all_of(self._finished_events)

        self._log.info("Shutting down")

    def shutdown(self):
        """Terminate the runtime.

        The runtime will not stop immediately but wait until all currently
        running applications terminate.
        """
        self._log.debug("Shutdown was requested")
        self._request_shutdown.succeed()

    @property
    def env(self):
        """The simpy environment"""
        return self.system.env

    def start_applications(self, graphs, traces):
        # clean up running applications first
        for name, app in self._running_applications.items():
            if app.is_finished():
                self._running_applications.pop(name)

        # Create random mappings for all the applications
        for graph, trace in zip(graphs, traces):
            rep = hydra.utils.instantiate(
                self.cfg["representation"], graph, self.system.platform
            )
            mapper = RandomMapper(graph, self.system.platform, trace, rep)
            mapping = mapper.generate_mapping()

            app = FiveGRuntimeDataflowApplication(
                name=graph.name,
                graph=graph,
                app_trace=trace,
                system=self.system,
            )

            self._log.debug(f"Launching the application {app.name}")
            self._running_applications[app.name] = app
            finished = self.env.process(app.run(mapping))
            self._finished_events.append(finished)
