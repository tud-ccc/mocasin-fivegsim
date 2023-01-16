fivegsim
========

A simualtor for 5G baseband applications based on mocasin.

Installation
------------

Assuming you have installed mocasin already, simply run `pip install .` in this
directory to install fivegsim. If you plan on changing the code in this
repository, you should install in developer mode with `pip install -e ."[dev]"`.

Usage
-----

To run the 5G simulator, you may use its own entry point called `fivegsim`. Note
that this entry point invoked with its own set of default settings. Running the
`fivegsim` command is equivalent to the following mocasin command.
```
mocasin simulate simulation_type=fivegsim mapper=static_cfs platform=odroid
```

Currently, `fivegsim` only works in conjunction with two platforms: `odroid`
and `odroid_acc`. In principle, other platforms can be supported, but this
requires generating additional traces for the core types of those other
platforms.

To specify the input trace, use the `trace_file` config key.
```
fivegsim trace_file=path/to/file
```

Fivegsim can also be used in conjunction with other mocasin tasks like
`generate_mapping`. For this, fivegsim provides an application which is a
single instance (one UE) of the PHY Benchmark. For instance, you can run the
following commands.
```
mocasin graph_to_dot graph=phybench
mocasin generate_mapping mapper=random platform=odroid graph=phybench trace=phybench platform.processor_0.type=ARM_CORTEX_A7 platform.processor_1.type=ARM_CORTEX_A15
```

The precise configuration of phybench can be overwritten as follows
```
mocasin generate_mapping mapper=random platform=odroid graph=phybench trace=phybench phybench.prbs=10 phybench.layers=10 phybench.modulation_scheme=4 platform.processor_0.type=ARM_CORTEX_A7 platform.processor_1.type=ARM_CORTEX_A15
```

There is also a possibility to generate a new LTE trace, which could be supplied
to the 5G simulator. To generate the new trace, run the following command.
```
python fivegsim/util/lte_trace_generator.py <# subframes (600)> <median_prbs (10)> <max_ue (3)> <period (1)>
```
