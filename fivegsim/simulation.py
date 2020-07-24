from pykpn.simulate import KpnSimulation


class FiveGSimulation(KpnSimulation):

    def __init__(self, platform, kpn, mapping, trace):
        super().__init__(platform, kpn, mapping, trace)

    @staticmethod
    def from_hydra(cfg):
        return KpnSimulation.from_hydra(cfg)


class HydraFiveGSimulation(FiveGSimulation):
    def __new__(cls, cfg):
        return FiveGSimulation.from_hydra(cfg)
