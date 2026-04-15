Logging convention
==================

All Nornir projects write persistent logs through a shared convention managed by ``nornir-shared``.
This page documents the required setup, the file layout that results, and the multiprocessing
extension for pool-based workloads.

Environment variable
--------------------

``NORNIR_LOG_ROOT``
    Root directory for all file logs.  If unset, logging falls back to **console only** and a
    warning is emitted.  Set this to a stable path before starting any Nornir process::

        $env:NORNIR_LOG_ROOT = 'D:\logs\nornir'   # PowerShell
        export NORNIR_LOG_ROOT=/var/log/nornir      # bash

Session file layout
-------------------

When ``NORNIR_LOG_ROOT`` is defined the library creates:

.. code-block:: text

    <NORNIR_LOG_ROOT>/
    └── <YYYY-MM-DD>/
        ├── nornir-session-<YYYYMMDD-HHMMSS>.log        ← all levels
        └── nornir-session-<YYYYMMDD-HHMMSS>-errors.log ← WARNING and above

One session ID is minted once per **parent process** and reused across any child processes
started in the same run (see multiprocessing section below).

Single-process setup
--------------------

Call ``nornir_shared.misc.SetupLogging`` as early as possible in your entry point::

    import nornir_shared.misc

    nornir_shared.misc.SetupLogging()   # reads NORNIR_LOG_ROOT automatically

All subsequent ``logging.getLogger(__name__)`` calls in any Nornir package will write to the
session files.  Use hierarchical logger names (e.g. ``nornir_buildmanager.operations.block``)
so log records carry project identity without needing separate files per project.

Multiprocessing setup
---------------------

Direct ``FileHandler`` writes from worker processes can interleave or corrupt log files under
heavy load.  Use the queue-listener pattern provided by ``nornir_shared.misc``:

.. code-block:: python

    import multiprocessing
    import nornir_shared.misc

    # --- Parent process ---
    queue = nornir_shared.misc.StartMultiprocessLoggingListener()
    # queue is a multiprocessing.Queue; pass it to each worker

    def worker_fn(log_queue):
        nornir_shared.misc.ConfigureWorkerQueueLogging(log_queue)
        # ... do work; logging calls go through the queue to the parent listener
        import logging
        logging.getLogger(__name__).info("worker log line")

    with multiprocessing.Pool(4, initializer=worker_fn,
                              initargs=(queue,)) as pool:
        pool.map(...)

    # --- Shutdown ---
    nornir_shared.misc.StopMultiprocessLoggingListener()

``nornir-pools`` process pools wire this automatically when a listener is active; you only need
to call ``StartMultiprocessLoggingListener`` in the parent before creating the pool.

Session inheritance
~~~~~~~~~~~~~~~~~~~

The parent sets ``NORNIR_LOG_SESSION_ID`` in the environment before spawning workers.  Workers
that call ``ConfigureWorkerQueueLogging`` inherit the same session ID and never create their own
log files.  If a worker is started standalone (without a parent listener), it falls back to
standard ``SetupLogging`` behavior.

Rules (enforced by the ``Unified-Logging-Convention`` Cursor rule)
------------------------------------------------------------------

- **Do not** create ad hoc debug files (``debug-*.log``, cwd log files, project-local directories).
- **Do not** hardcode absolute log paths in project modules; always use ``NORNIR_LOG_ROOT``.
- ``nornir_shared.prettyoutput`` is for user-facing **console/UI presentation** only; it must
  not own file log sinks.
- Project identity belongs in the **logger name** (e.g. ``pyre.ui.stoswindow``), not in the
  log file name.
- In worker processes, attach **only** a ``QueueHandler``; do not attach additional
  ``FileHandler`` instances.

.. seealso::

   :doc:`../packages/nornir_shared` — package overview including logging utilities.
