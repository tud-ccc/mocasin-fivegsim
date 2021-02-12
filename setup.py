# Copyright (C) 2020 TU Dresden
# All rights reserved
#
# Authors: Christian Menard

from setuptools import setup, find_namespace_packages, find_packages

project_name = "fivegsim"
version = "0.1.0"

setup(
    name=project_name,
    version=version,
    packages=find_packages(exclude=["test", "*.test"])
    + find_namespace_packages(include=["hydra_plugins.*"]),
    install_requires=[
        "mocasin",
        "mocasin-maps-examples",
        "hydra-core<1.1.0",
        "numpy",
    ],
    setup_requires=["pytest-runner"],
    tests_require=["pytest", "pytest_mock", "mocasin-maps-examples"],
    include_package_data=True,
)
