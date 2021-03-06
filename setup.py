# Copyright (C) 2020 TU Dresden
# Licensed under the ISC license (see LICENSE.txt)
#
# Authors: Christian Menard

from setuptools import setup, find_namespace_packages, find_packages
import sys

project_name = "fivegsim"
version = "0.1.0"

setup(
    name=project_name,
    version=version,
    packages=find_packages(exclude=["test", "*.test"])
    + find_namespace_packages(include=["hydra_plugins.*"]),
    install_requires=[
        "mocasin",
        "hydra-core",
        "numpy",
    ],
    setup_requires=["pytest-runner"],
    tests_require=["pytest<7.0" if sys.version_info < (3, 7) else "pytest"],
    entry_points={
        "console_scripts": [
            "fivegsim=fivegsim.__main__:main",
        ]
    },
    include_package_data=True,
)
