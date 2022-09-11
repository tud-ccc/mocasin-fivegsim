# Copyright (C) 2020 TU Dresden
# Licensed under the ISC license (see LICENSE.txt)
#
# Authors: Felix Teweleit, Andres Goens, Christian Menard

import copy

from hydra.utils import instantiate

from mocasin.common.platform import Platform, Processor
from mocasin.platforms.platformDesigner import PlatformDesigner


class OdroidWithAccelerators(Platform):
    def __init__(
        self,
        processor_0,
        processor_1,
        processor_fft_acc,
        processor_mf_acc,
        processor_wind_acc,
        processor_ant_acc,
        processor_comb_acc,
        processor_demap0_acc,
        processor_demap1_acc,
        processor_demap2_acc,
        processor_demap3_acc,
        processor_demap4_acc,
        num_big=4,
        num_little=4,
        num_fft_acc=2,
        num_mf_acc=2,
        num_wind_acc=2,
        num_ant_acc=2,
        num_comb_acc=2,
        num_demap0_acc=2,
        num_demap1_acc=2,
        num_demap2_acc=2,
        num_demap3_acc=2,
        num_demap4_acc=2,
        name="odroid_acc",
        peripheral_static_power=0.7633,
        **kwargs,
    ):

        # workaraound for Hydra < 1.1
        if not isinstance(processor_0, Processor):
            processor_0 = instantiate(processor_0)
        if not isinstance(processor_1, Processor):
            processor_1 = instantiate(processor_1)
        if not isinstance(processor_fft_acc, Processor):
            processor_fft_acc = instantiate(processor_fft_acc)
        if not isinstance(processor_mf_acc, Processor):
            processor_mf_acc = instantiate(processor_mf_acc)
        if not isinstance(processor_wind_acc, Processor):
            processor_wind_acc = instantiate(processor_wind_acc)
        if not isinstance(processor_ant_acc, Processor):
            processor_ant_acc = instantiate(processor_ant_acc)
        if not isinstance(processor_comb_acc, Processor):
            processor_comb_acc = instantiate(processor_comb_acc)
        if not isinstance(processor_demap0_acc, Processor):
            processor_demap0_acc = instantiate(processor_demap0_acc)
        if not isinstance(processor_demap1_acc, Processor):
            processor_demap1_acc = instantiate(processor_demap1_acc)
        if not isinstance(processor_demap2_acc, Processor):
            processor_demap2_acc = instantiate(processor_demap2_acc)
        if not isinstance(processor_demap3_acc, Processor):
            processor_demap3_acc = instantiate(processor_demap3_acc)
        if not isinstance(processor_demap4_acc, Processor):
            processor_demap4_acc = instantiate(processor_demap4_acc)
        super().__init__(name, kwargs.get("symmetries_json", None))

        designer = PlatformDesigner(self)
        designer.setSchedulingPolicy("FIFO", 1000)
        designer.newElement("exynos5422")

        # cluster 0 with l2 cache
        designer.addPeClusterForProcessor("cluster_a7", processor_0, num_little)
        # Add L1/L2 caches
        designer.addCacheForPEs(
            "cluster_a7",
            readLatency=1,
            writeLatency=1,
            readThroughput=8,
            writeThroughput=8,
            frequencyDomain=processor_0.frequency_domain.frequency,
            name="L1_A7",
        )
        designer.addCommunicationResource(
            name="L2_A7",
            clusterIds=["cluster_a7"],
            readLatency=21,
            writeLatency=21,
            readThroughput=8,
            writeThroughput=8,
            frequencyDomain=processor_0.frequency_domain.frequency,
        )

        # cluster 1, with l2 cache
        designer.addPeClusterForProcessor("cluster_a15", processor_1, num_big)
        # Add L1/L2 caches
        designer.addCacheForPEs(
            "cluster_a15",
            readLatency=1,
            writeLatency=1,
            readThroughput=8,
            writeThroughput=8,
            frequencyDomain=processor_1.frequency_domain.frequency,
            name="L1_A15",
        )
        # L2 latency is L1 latency plus 21 cycles
        designer.addCommunicationResource(
            "L2_A15",
            ["cluster_a15"],
            readLatency=22,
            writeLatency=22,
            readThroughput=8,
            writeThroughput=8,
            frequencyDomain=processor_1.frequency_domain.frequency,
        )

        # cluster 2 (accelerators), no caches
        designer.addPeClusterForProcessor(
            "cluster_fft_acc", processor_fft_acc, num_fft_acc
        )
        designer.addPeClusterForProcessor(
            "cluster_mf_acc", processor_mf_acc, num_mf_acc
        )
        designer.addPeClusterForProcessor(
            "cluster_wind_acc", processor_wind_acc, num_wind_acc
        )
        designer.addPeClusterForProcessor(
            "cluster_ant_acc", processor_ant_acc, num_ant_acc
        )
        designer.addPeClusterForProcessor(
            "cluster_comb_acc", processor_comb_acc, num_comb_acc
        )
        designer.addPeClusterForProcessor(
            "cluster_demap0_acc", processor_demap0_acc, num_demap0_acc
        )
        designer.addPeClusterForProcessor(
            "cluster_demap1_acc", processor_demap1_acc, num_demap1_acc
        )
        designer.addPeClusterForProcessor(
            "cluster_demap2_acc", processor_demap2_acc, num_demap2_acc
        )
        designer.addPeClusterForProcessor(
            "cluster_demap3_acc", processor_demap3_acc, num_demap3_acc
        )
        designer.addPeClusterForProcessor(
            "cluster_demap4_acc", processor_demap4_acc, num_demap4_acc
        )

        # RAM connecting all clusters
        # RAM latency is L2 latency plus 120 cycles
        designer.addCommunicationResource(
            "DRAM",
            [
                "cluster_a7",
                "cluster_a15",
                "cluster_fft_acc",
                "cluster_mf_acc",
                "cluster_wind_acc",
                "cluster_ant_acc",
                "cluster_comb_acc",
                "cluster_demap0_acc",
                "cluster_demap1_acc",
                "cluster_demap2_acc",
                "cluster_demap3_acc",
                "cluster_demap4_acc",
            ],
            readLatency=142,
            writeLatency=142,
            readThroughput=8,
            writeThroughput=8,
            frequencyDomain=933000000.0,
        )
        designer.finishElement()

        # Reduce the scheduling cycles for the accelerators
        for scheduler in self.schedulers():
            if scheduler.processors[0].type.startswith("acc:"):
                # need to copy the policy first, because the designer assigns
                # each scheduler the same policy object
                scheduler.policy = copy.deepcopy(scheduler.policy)

                # FIXME: the 50 cycles is just a guess and it might need
                # adjustment
                # accelerators use 50 cycles for task switching
                scheduler.policy.scheduling_cycles = 50

        # Set peripheral static power of the platform.
        designer.setPeripheralStaticPower(peripheral_static_power)
