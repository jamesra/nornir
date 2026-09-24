Profiling
=========

Use the shared profiler instead of ad hoc log files. File output follows :doc:`../development/logging` and ``NORNIR_LOG_ROOT``.

* ``nornir_shared.profiling.PhaseProfiler`` records named phases. ``configure_phase_profiler`` installs one for the process; ``phase`` is the context manager. Relative log paths land in the session directory when ``NORNIR_LOG_ROOT`` is set.
* ``NORNIR_PROFILE``, when set to a directory, turns on multiprocess profiling output from ``nornir_pools``. If the value is set but is not a usable path, the library may fall back to a temporary directory. If it is unset, that profiling output stays off.
* ``NORNIR_POOL_DIAG=1`` logs pool lifecycle events. See :doc:`pools`.
* ``NORNIR_REFINE_PHASE_TIMING=1`` makes mosaic grid refine log per-pass time for prewarp, cell extract, FFT, host sync, regularize, and apply. The harness that sets it is ``nornir-imageregistration/scripts/microbench_mosaic_refine.py``.

Pyre registration should stay interactive: on the order of a second per control point for a point align. If a change to point registration or grid refine misses that, profile the phase list before retuning thresholds.
