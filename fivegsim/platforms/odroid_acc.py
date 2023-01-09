# Copyright (C) 2020 TU Dresden
# Licensed under the ISC license (see LICENSE.txt)
#
# Authors: Felix Teweleit, Andres Goens, Christian Menard, Julian Robledo

import copy

from hydra.utils import instantiate

from mocasin.common.platform import Platform, Processor
from mocasin.platforms.platformDesigner import PlatformDesigner, cluster
from mocasin.platforms.odroid import makeOdroid, peParams


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
        processor_demap1_acc,
        processor_demap2_acc,
        processor_demap4_acc,
        processor_demap6_acc,
        processor_demap8_acc,
        num_big=4,
        num_little=4,
        num_fft_acc=2,
        num_mf_acc=0,
        num_wind_acc=0,
        num_ant_acc=0,
        num_comb_acc=0,
        num_demap1_acc=0,
        num_demap2_acc=0,
        num_demap4_acc=0,
        num_demap6_acc=0,
        num_demap8_acc=0,
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
        if not isinstance(processor_demap1_acc, Processor):
            processor_demap1_acc = instantiate(processor_demap1_acc)
        if not isinstance(processor_demap2_acc, Processor):
            processor_demap2_acc = instantiate(processor_demap2_acc)
        if not isinstance(processor_demap4_acc, Processor):
            processor_demap4_acc = instantiate(processor_demap4_acc)
        if not isinstance(processor_demap6_acc, Processor):
            processor_demap6_acc = instantiate(processor_demap6_acc)
        if not isinstance(processor_demap8_acc, Processor):
            processor_demap8_acc = instantiate(processor_demap8_acc)
        super().__init__(name, kwargs.get("symmetries_json", None))

        # Start platform designer
        designer = PlatformDesigner(self)
        exynos_acc = makeOdroid(
            name,
            designer,
            processor_0,
            processor_1,
            peripheral_static_power,
            num_little,
            num_big,
        )

        # cluster accelerators, no L1 memory
        cluster_acc = cluster("cluster_acc", designer)
        exynos_acc.addCluster(cluster_acc)
        for i in range(num_fft_acc):
            cluster_acc.addPeToCluster(
                f"fft_{i:02d}", *(peParams(processor_fft_acc))
            )
        for i in range(num_mf_acc):
            cluster_acc.addPeToCluster(
                f"mf_{i:02d}", *(peParams(processor_mf_acc))
            )
        for i in range(num_wind_acc):
            cluster_acc.addPeToCluster(
                f"wind_{i:02d}", *(peParams(processor_wind_acc))
            )
        for i in range(num_ant_acc):
            cluster_acc.addPeToCluster(
                f"ant_{i:02d}", *(peParams(processor_ant_acc))
            )
        for i in range(num_comb_acc):
            cluster_acc.addPeToCluster(
                f"comb_{i:02d}", *(peParams(processor_comb_acc))
            )
        for i in range(num_demap1_acc):
            cluster_acc.addPeToCluster(
                f"demap1_{i:02d}", *(peParams(processor_demap1_acc))
            )
        for i in range(num_demap2_acc):
            cluster_acc.addPeToCluster(
                f"demap2_{i:02d}", *(peParams(processor_demap2_acc))
            )
        for i in range(num_demap4_acc):
            cluster_acc.addPeToCluster(
                f"demap4_{i:02d}", *(peParams(processor_demap4_acc))
            )
        for i in range(num_demap6_acc):
            cluster_acc.addPeToCluster(
                f"demap6_{i:02d}", *(peParams(processor_demap6_acc))
            )
        for i in range(num_demap8_acc):
            cluster_acc.addPeToCluster(
                f"demap8_{i:02d}", *(peParams(processor_demap8_acc))
            )

        pes = cluster_acc.getProcessors()
        ram = exynos_acc.findComRes("DRAM")
        for pe in pes:
            designer.connectComponents(pe, ram)

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
        # designer.setPeripheralStaticPower(peripheral_static_power)

        self.generate_all_primitives()
