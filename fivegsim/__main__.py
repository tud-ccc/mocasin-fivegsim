#!/usr/bin/env python3

# Copyright (C) 2021 TU Dresden
# All rights reserved
#
# Authors: Christian Menard

import hydra

from mocasin.tasks.simulate import simulate


@hydra.main(config_path="conf", config_name="fivegsim")
def main(cfg):
    simulate(cfg)


if __name__ == "__main__":
    main()
