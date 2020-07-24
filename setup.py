from setuptools import setup, find_packages

setup(
    name="fivegsim",
    version="0.0.1",
    packages=find_packages(),
    install_requires=[],
    setup_requires=['pykpn'],
    include_package_data=True,
)
