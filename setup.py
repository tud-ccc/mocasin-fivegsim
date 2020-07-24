from setuptools import setup, find_packages
import sys

requires = []
if sys.version_info.minor < 7:
    requires.append("importlib-resources")

setup(
    name="fivegsim",
    version="0.0.1",
    packages=find_packages(),
    install_requires=requires + [],
    setup_requires=['pykpn'],
    include_package_data=True,
)
