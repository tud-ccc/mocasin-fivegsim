# Copyright (C) 2021 TU Dresden
# Licensed under the ISC license (see LICENSE.txt)
#
# Authors: Robert Khasanov

from collections import Counter
import logging

from mocasin.common.mapping import Mapping, ProcessMappingInfo
from mocasin.mapper import BaseMapper
from mocasin.mapper.partial import ComPartialMapper
from mocasin.mapper.random import RandomPartialMapper


log = logging.getLogger(__name__)


class FiveGMapper(BaseMapper):
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

    def __init__(self, platform):
        super().__init__(platform, True)
        self.randMapGen = RandomPartialMapper(self.platform)
        self.comMapGen = ComPartialMapper(self.platform, self.randMapGen)

    def _map_to_core(self, mapping, process, core):
        scheduler = list(self.platform.schedulers())[0]
        affinity = core
        priority = 0
        info = ProcessMappingInfo(scheduler, affinity, priority)
        mapping.add_process_info(process, info)

    def _remap_accelerators(
        self,
        graph,
        trace,
        mapping_dict,
        accelerators,
        phase,
        acc_kernels,
        processor_time,
    ):
        """Remap fft nodes to accelerators.

        Remapping is done iteratively, the algorithm takes the generic core with
        the longest execution time and remaps it to the accelerator with the
        least execution time.
        """
        num_instances = graph.structure[phase]["num_instances"]
        subkernels = graph.structure[phase]["subkernels"]
        regular_processors = list(processor_time.keys())

        # Before fft there might be some other processes, during this time
        # the accelerator is idle
        offset = 0
        for subkernel in subkernels:
            if subkernel in acc_kernels:
                break
            acc_cycles = Counter(
                trace.accumulate_processor_cycles(f"{subkernel}0")
            )
            offset += min(
                [pe.ticks(acc_cycles[pe.type]) for pe in regular_processors]
            )

        for acc in accelerators:
            processor_time[acc] = offset

        for subkernel in subkernels:
            if subkernel not in acc_kernels:
                continue
            acc_cycles = Counter(
                trace.accumulate_processor_cycles(f"{subkernel}0")
            )
            # pe -> num_instances
            subkernel_instances = {
                pe: [] for pe in regular_processors + accelerators
            }
            for i in range(num_instances):
                process = graph.find_process(f"{subkernel}{i}")
                pe = mapping_dict[process]
                subkernel_instances[pe].append(process)
            # pe -> time of subkernel
            subkernel_time = {}
            for pe in regular_processors + accelerators:
                subkernel_time[pe] = pe.ticks(acc_cycles[pe.type])

            while True:
                filtered_processors = [
                    pe for pe in regular_processors if subkernel_instances[pe]
                ]
                if not filtered_processors:
                    break
                pe_max = max(filtered_processors, key=processor_time.get)
                acc_min = min(accelerators, key=processor_time.get)
                assert pe_max in regular_processors

                # check that after miggration accelerator time will not exceed
                # the processor time
                moved_processor_time = processor_time.copy()
                moved_processor_time[pe_max] -= subkernel_time[pe_max]
                moved_processor_time[acc_min] += subkernel_time[acc_min]
                new_pe_max = max(
                    moved_processor_time, key=moved_processor_time.get
                )
                if new_pe_max in regular_processors:
                    processor_time[pe_max] -= subkernel_time[pe_max]
                    processor_time[acc_min] += subkernel_time[acc_min]
                    process = subkernel_instances[pe_max].pop()
                    subkernel_instances[acc_min].append(process)
                    mapping_dict[process] = acc_min
                else:
                    break

        return processor_time

    def _map_phase(self, graph, trace, mapping_dict, phase, processors):
        """Map processes in the specific phase.

        Args:
            mapping_dict (dict): currently constructed mapping_dict
            phase (str): a phase name
            processors (list of `Processor`): a list of processors to map to.

        Returns: a tuple (execution time, dynamic energy) of the phase
        """
        log.debug(f"Mapping phase: {phase}")
        num_instances = graph.structure[phase]["num_instances"]
        subkernels = graph.structure[phase]["subkernels"]

        # filter regular processors
        regular_processors = [
            pe for pe in processors if not pe.type.startswith("acc_")
        ]
        # execution time of already mapped processes
        processor_time = Counter(dict.fromkeys(regular_processors, 0))

        # collect the amount of cycles at each core for the whole kernel
        acc_cycles = Counter()
        for kernel in subkernels:
            acc_cycles += Counter(
                trace.accumulate_processor_cycles(f"{kernel}0")
            )
        phase_processor_cycles = Counter()
        for pe in regular_processors:
            phase_processor_cycles[pe] = acc_cycles[pe.type]

        # add context switsch cycles
        for scheduler in self.platform.schedulers():
            for pe in scheduler.processors:
                if pe not in regular_processors:
                    continue
                phase_context_switch_cycles = (
                    scheduler.policy.scheduling_cycles * len(subkernels)
                )
                phase_processor_cycles[pe] += phase_context_switch_cycles

        # transform cycles to ticks
        phase_processor_time = Counter()
        for pe in regular_processors:
            phase_processor_time[pe] = pe.ticks(phase_processor_cycles[pe])

        # perform load balancing
        processor_instances = dict.fromkeys(regular_processors, 0)
        for _ in range(num_instances):
            pe_time_added = processor_time + phase_processor_time
            pe_min = min(
                pe_time_added,
                key=pe_time_added.get,
                default=regular_processors[0],
            )
            processor_instances[pe_min] += 1
            processor_time[pe_min] += phase_processor_time[pe_min]

        # assign cores to the processes
        i = 0
        for pe, count in processor_instances.items():
            for _ in range(count):
                for subkernel in subkernels:
                    process = graph.find_process(f"{subkernel}{i}")
                    mapping_dict[process] = pe
                i += 1

        assert i == num_instances

        # remap to accelerators
        accelerators = [pe for pe in processors if pe.type.startswith("acc_")]
        if accelerators:
            assert len(set(pe.type for pe in accelerators)) == 1
            acc_kernels = accelerators[0].type[4:].split(",")
            if any(subkernel in acc_kernels for subkernel in subkernels):
                processor_time = self._remap_accelerators(
                    graph,
                    trace,
                    mapping_dict,
                    accelerators,
                    phase,
                    acc_kernels,
                    processor_time,
                )

        exec_time = max(processor_time.values(), default=0)
        # estimate energy
        dynamic_energy = 0
        for pe in regular_processors:
            dynamic_energy += processor_time[pe] * pe.dynamic_power()

        return exec_time, dynamic_energy

    def generate_mapping(
        self,
        graph,
        trace=None,
        representation=None,
        processors=None,
        partial_mapping=None,
    ):
        """Generate the mapping for the graph.

        Args:
        :param graph: a dataflow graph
        :type graph: DataflowGraph
        :param trace: a trace generator
        :type trace: TraceGenerator
        :param representation: a mapping representation object
        :type representation: MappingRepresentation
        :param processors: list of processors to map to.
        :type processors: a list[Processor]
        :param partial_mapping: a partial mapping to complete
        :type partial_mapping: Mapping

        """
        regular_processors = [
            pe for pe in processors if not pe.type.startswith("acc_")
        ]

        if not regular_processors:
            return None

        exec_time = 0
        dynamic_energy = 0

        mapping_dict = {}

        # map applications phase by phase
        for phase in graph.structure:
            phase_results = self._map_phase(
                graph, trace, mapping_dict, phase, processors
            )
            exec_time += phase_results[0]
            dynamic_energy += phase_results[1]

        mapping = Mapping(graph, self.platform)
        for process, pe in mapping_dict.items():
            self._map_to_core(mapping, process, pe)
        mapping = self.comMapGen.generate_mapping(
            graph,
            trace=trace,
            representation=representation,
            partial_mapping=mapping,
        )

        mapping.metadata.exec_time = exec_time / 1000000000.0
        mapping.metadata.energy = dynamic_energy / 1000000000.0
        return mapping
