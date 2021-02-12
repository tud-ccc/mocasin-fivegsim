fivegsim
========

A simualtor for 5G baseband applications based on mocasin.

Installation
------------

Assuming you have installed mocasin and mocasin-maps-examples already, simply
run `pip install .` in this directory to install fivegsim. If you plan on
changing the code in this repository, you should install in developer mode with
`pip install -e .`.

Usage
-----

Running the 5G simulator is as simple as running `fivegsim`. Note that fivegsim
provides its own entry point with its own set of default settings. Running the
`fivegsim` command is equivalent to the following mocasin command.
```
mocasin simulate simulation_type=fivegsim mapper=static_cfs platform=maps_exynos
```

By default fivegsim reads the example trace in
`fivegsim/files/slicedtrace30BS.txt`. Another trace can be specified
using the `trace_file` config key.
```
fivegsim trace_file=path/to/file
```

Fivegsim can also be used in conjunction with other mocasin tasks like
`generate_mapping`. For this, fivegsim provides an application which is a
single instance (one UE) of the PHY Benchmark. For instance, you can run the
following commands.
```
moasin graph_to_dot graph=phybench
mocasin generate_mapping mapper=random platform=maps_exynos graph=phybench trace=phybench
```

The precise configuration of phybench can be overwritten as follows
```
mocasin generate_mapping mapper=random platform=maps_exynos graph=phybench trace=phybench phybench.prbs=10 phybench.layers=10 phybench.modulation_scheme=4
```

Also note that fivegsim only works in conjunction with the `maps_exynos`
platform at the moment. In principle, other platforms can be supported, but
this requires generating additional traces for the core types of those other
platforms.

