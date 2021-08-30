# Copyright (C) 2021 TU Dresden
# Licensed under the ISC license (see LICENSE.txt)
#
# Authors: Robert Khasanov, Christian Menard

import logging
import itertools

from mocasin.common.mapping import (
    Mapping,
    ChannelMappingInfo,
    ProcessMappingInfo,
)
from mocasin.simulate.manager import RuntimeManager

from fivegsim.simulate import FiveGRuntimeDataflowApplication

log = logging.getLogger(__name__)


class PhybenchLoadBalancer(RuntimeManager):
    def __init__(self, system, cfg, stats):
        super().__init__(system, stats)
        self.cfg = cfg

        platform = system.platform

        # keep track of all running applications
        self._running_applications = {}

        # an indicating that the runtime should wake
        self._wake_up = self.env.event()

        # a list to keep track of all events indicating when an app finished
        self._finished_events = []

        # a cyclic iterator over all processors in the platform
        self._processor_iterator = iter(itertools.cycle(platform.processors()))

        # FIXME: should not access a private variable here
        self._schedulers = system._schedulers

        # register callbacks to get notified when a scheduler becomes idle
        for scheduler in self._schedulers:
            scheduler.idle.callbacks.append(self._scheduler_idle_callback)

    @property
    def name(self):
        """The runtime manager name."""
        return "Load Balancer"

    def run(self):
        """A simpy process modelling the actual runtime."""
        self._log.info("Starting up")

        while True:
            yield self.env.any_of([self._wake_up, self._request_shutdown])

            # break out of loop if shutdown was requested
            if self._request_shutdown.triggered:
                break

            # yield to ensure that all schedulers where notified and are aware
            # of the new apps and ready processes
            yield self.env.timeout(0)

            self._log.debug("Looking for idle schedulers.")

            for scheduler in self._schedulers:
                if scheduler.is_idle:
                    self._log.debug(f"scheduler {scheduler.name} is idle")
                    self._steal_task(scheduler)

        # wait for all applications to terminate
        yield self.env.all_of(self._finished_events)

        self._log.info("Shutting down")

    def start_applications(self, graphs, traces):
        # clean up running applications first
        for name, app in list(self._running_applications.items()):
            if app.is_finished():
                self._running_applications.pop(name)

        # Create random mappings for all the applications
        for graph, trace in zip(graphs, traces):
            # create a statistics entry for the application
            deadline = self.env.now + graph.timeout
            stats_entry = self.statistics.new_application(
                graph, arrival=self.env.now, deadline=deadline
            )
            # FIXME: There should be a way to set this when creating the entry
            # (or make true the default value)
            stats_entry.accepted = True
            processor = next(self._processor_iterator)
            # don't map on accelerators
            while processor.type.startswith("acc"):
                processor = next(self._processor_iterator)
            # create the mapping
            mapping = self._generate_single_core_mapping(
                graph, trace, processor
            )

            app = FiveGRuntimeDataflowApplication(
                name=graph.name,
                graph=graph,
                app_trace=trace,
                system=self.system,
                deadline=deadline,
                stats_entry=stats_entry,
            )

            self._log.debug(f"Launching the application {app.name}")
            self._running_applications[app.name] = app
            finished = self.env.process(app.run(mapping))
            self._finished_events.append(finished)

        # notify the event
        self._wake_up.succeed()
        self._wake_up = self.env.event()

    def _generate_single_core_mapping(self, graph, trace, processor):
        self._log.debug(f"Mapping {graph.name} to processor {processor.name}")

        platform = self.system.platform
        scheduler = platform.find_scheduler_for_processor(processor)

        mapping = Mapping(graph, platform)

        for p in graph.processes():
            process_mapping_info = ProcessMappingInfo(scheduler, processor)
            mapping.add_process_info(p, process_mapping_info)

        primitive = self._find_best_primitive(processor, processor)

        for c in graph.channels():
            channel_info = ChannelMappingInfo(primitive, 16)
            mapping.add_channel_info(c, channel_info)

        return mapping

    def _find_best_primitive(self, src, sink):
        # find all suitable_primitives
        suitable_primitives = []
        for primitive in self.system.platform.primitives():
            if primitive.is_suitable(src, [sink]):
                suitable_primitives.append(primitive)

        # return the best one
        suitable_primitives.sort(key=lambda p: p.static_costs(src, sink))
        return suitable_primitives[0]

    def _scheduler_idle_callback(self, event):
        scheduler = event.value
        self._log.debug(f"Scheduler {scheduler.name} became idle")
        # register the callback again
        scheduler.idle.callbacks.append(self._scheduler_idle_callback)
        # and try to steal something to work on
        self._steal_task(scheduler)

    def _scheduler_ready_callback(self, _):
        self._log.debug("A scheduler has new ready processes")
        # wake up
        self._wake_up.succeed()
        self._wake_up = self.env.event()

    def _steal_task(self, scheduler):
        busy_schedulers = [s for s in self._schedulers if not s.is_idle]
        # abort if no one is busy
        if len(busy_schedulers) == 0:
            return

        is_acc = scheduler._processor.type.startswith("acc_")
        if is_acc:
            processor_type = scheduler._processor.type
            acc_tasks = processor_type[4:].split(",")

        found_task_to_steal = False
        ready_events = []
        # iterate over all busy schedulers
        for busy_scheduler in busy_schedulers:
            # check if the scheduler has ready tasks
            # FIXME: should not access private member directly
            process = None
            if len(busy_scheduler._ready_queue) > 0:
                if is_acc:
                    # if we are stealing tasks for an accelerator, then we can
                    # only steal those tasks supported by the accelerator. Thus
                    # we need to actively search for a fitting task
                    for p in busy_scheduler._ready_queue:
                        if p.name.startswith(tuple(acc_tasks)):
                            process = p
                            break
                else:
                    process = busy_scheduler._ready_queue[0]
            if process:
                self._log.debug(
                    f"{scheduler.name} steals {process.name} from "
                    f"{busy_scheduler.name}"
                )
                found_task_to_steal = True

                app = process.app

                # move the task
                # FIXME: should not access private member directly
                from_processor = busy_scheduler._processor
                to_processor = scheduler._processor
                self.system.move_process(process, from_processor, to_processor)
                app._process_mappings[process] = to_processor

                # and update its primitives
                # FIXME: should not access private member directly
                for channel_ref in process._channels.values():
                    channel = channel_ref()
                    # the algorithm only works for channels with a single sink
                    assert len(channel._sinks) == 1

                    src_process = channel._src()
                    sink_process = channel._sinks[0]()

                    src_processor = app._process_mappings[src_process]
                    sink_processor = app._process_mappings[sink_process]

                    channel._primitive = self._find_best_primitive(
                        src_processor, sink_processor
                    )

            else:
                ready_events.append(busy_scheduler.process_ready)

        if not found_task_to_steal:
            self._log.debug(
                f"Did not find a task to steal for {scheduler.name}"
            )
            if len(ready_events) > 0:
                self.env.any_of(ready_events).callbacks.append(
                    self._scheduler_ready_callback
                )
