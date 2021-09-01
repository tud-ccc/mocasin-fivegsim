# Copyright (C) 2020 TU Dresden
# Licensed under the ISC license (see LICENSE.txt)
#
# Authors: Christian Menard

import os
import fivegsim

from hydra.plugins.search_path_plugin import SearchPathPlugin
from omegaconf import OmegaConf


class FiveGSimSearchPathPlugin(SearchPathPlugin):
    def __init__(self):
        # register a custom resolver to resolve paths to files located within
        # the fivegsim package
        OmegaConf.register_new_resolver(
            "fivegsim_path",
            lambda path="": os.path.join(
                os.path.dirname(fivegsim.__file__), path
            ),
        )

    def manipulate_search_path(self, search_path):
        search_path.append(
            provider="fivegsim",
            path="pkg://fivegsim.conf",
            anchor="main",
        )
