# Copyright (C) 2020 TU Dresden
# All Rights Reserved
#
# Authors: Christian Menard

import importlib.resources

from hydra.plugins.search_path_plugin import SearchPathPlugin


class FiveGSimSearchPathPlugin(SearchPathPlugin):

    def __init__(self):
        super().__init__()
        # importlib returns a contextmanager that is intended for use in a with
        # statement. Since we have no control over the lifetime of this plugin,
        # we manually enter the context on __init__ and exit it on __del__
        self.path_cm = importlib.resources.path('fivegsim', 'conf')
        self.path = str(self.path_cm.__enter__())

    def manipulate_search_path(self, search_path):
        search_path.append(
            provider="fivegsim-searchpath-plugin", path=self.path, anchor="main")

    def __del__(self):
        self.path_cm.__exit__(None, None, None)
