# Copyright (C) 2020 TU Dresden
# All Rights Reserved
#
# Authors: Christian Menard

import sys
if sys.version_info.minor < 7:
    import importlib_resources as ilr
else:
    import importlib.resources as ilr

from hydra.plugins.search_path_plugin import SearchPathPlugin


class FiveGSimSearchPathPlugin(SearchPathPlugin):

    def __init__(self):
        super().__init__()
        # importlib returns a contextmanager that is intended for use in a with
        # statement. Since we have no control over the lifetime of this plugin,
        # we manually enter the context on __init__ and exit it on __del__
        self.path_cm = ilr.path('fivegsim', 'conf')
        self.path = str(self.path_cm.__enter__())

    def manipulate_search_path(self, search_path):
        search_path.append(
            provider="fivegsim-searchpath-plugin", path=self.path, anchor="main")

    def __del__(self):
        self.path_cm.__exit__(None, None, None)
