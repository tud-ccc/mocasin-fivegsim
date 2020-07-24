# Copyright (C) 2020 TU Dresden
# All Rights Reserved
#
# Authors: Christian Menard

import importlib.resources

from hydra.plugins.search_path_plugin import SearchPathPlugin


class FiveGSimSearchPathPlugin(SearchPathPlugin):

    def manipulate_search_path(self, search_path):
        path = str(importlib.resources.path('fivegsim', 'conf').__enter__())
        search_path.append(
            provider="fivegsim-searchpath-plugin", path=path, anchor="main")
