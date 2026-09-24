nornir-shared
=============

``nornir_shared`` is the common utilities package used by every other Nornir project.  It owns
the **logging convention**, console/UI output helpers, filesystem utilities, and lightweight
parallelism helpers that do not belong in any single domain package.

* **Repository:** ``nornir-shared/``
* **Python import:** ``nornir_shared``

Key modules
-----------

``nornir_shared.misc``
~~~~~~~~~~~~~~~~~~~~~~

The primary utilities module.  Key APIs:

``SetupLogging()``
    Initialise file logging for the current process.  Reads ``NORNIR_LOG_ROOT`` to determine
    the root directory for session log files.  Safe to call multiple times (idempotent handlers).

``StartMultiprocessLoggingListener()``
    Start a queue-based logging listener in the parent process before spawning workers.
    Returns the ``multiprocessing.Queue`` to pass to workers.

``ConfigureWorkerQueueLogging(queue)``
    Call in each worker process to route all log records through the shared queue to the
    parent listener (avoids concurrent file writes).

``StopMultiprocessLoggingListener()``
    Gracefully shut down the listener after all workers have finished.

See :doc:`../development/logging` for the full logging guide, including environment variables,
session file layout, and multiprocessing patterns.

``nornir_shared.prettyoutput``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Console and UI presentation helpers (progress indicators, coloured status lines).
**Not** a logging sink — do not use this module to write persistent log files.

``nornir_shared.filesystem``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Filesystem utilities used by buildmanager and imageregistration: path normalisation, directory
creation helpers, and checksum utilities.

``nornir_shared.plot``
~~~~~~~~~~~~~~~~~~~~~~

Shared matplotlib plotting helpers (histograms, overlay images) used by imageregistration
and buildmanager for diagnostic output.

Environment variables
---------------------

``NORNIR_LOG_ROOT``
    Root directory for all Nornir file logs.  Required for persistent logging; omit to get
    console-only output.  See :doc:`../development/logging`.

**API reference:** :doc:`../api/nornir_shared`
