fivegsim
========

A simualtor for 5G baseband applications based on pykpn.

Installation
------------

First you need to setup pykpn in a virtual environment as described in the
pykpn README. Make sure to checkout the 'simulate' branch of pykpn. Otherwise
fivegsim will not work.

Be sure that the virtual environment containing the pykpn installation is activated. Then you can setup fivegsim:
```
python setup.py develop
```

Run
---

To run a simulation, switch to the examples directory of pykpn. This ensures
that the example platforms are visible to pykpn. Then run:
```
pykpn simulate platform=exynos simulation_type=fivegsim
```

This will run the 5G simulation defined by this package. Note that you can give
additional `app` or `trace` parameters, but those will be ignored. Also note
that fivegsim only works in conjuntion with the exynos platform at the
moment. In principle, other platforms can be supported, but this requires
generating additional traces for the core types of those other platforms.


