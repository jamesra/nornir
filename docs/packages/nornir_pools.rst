nornir-pools
============

Thread, process, subprocess, and cluster **pool** abstractions so the same task code can run
locally on threads or processes, or remotely on a cluster, with minimal code changes.

This section consolidates the former standalone **Nornir Pools** doc tree.

Pool backends
-------------

``nornir_pools`` provides a consistent ``add_task`` / ``wait_return`` interface over four
different execution backends:

.. list-table::
   :header-rows: 1
   :widths: 25 30 45

   * - Backend
     - Entry point
     - Notes
   * - **threading**
     - ``GetGlobalThreadPool()``
     - Python threads; subject to the GIL for CPU-bound work but lightweight for I/O.
   * - **multiprocessing**
     - ``GetGlobalMultiprocessPool()``
     - Separate OS processes; bypasses the GIL; uses ``multiprocessing`` module.
   * - **subprocess**
     - ``GetGlobalSerialPool()`` / subprocess variants
     - Runs tasks as child processes via ``subprocess``; useful for calling external tools.
   * - **Parallel Python (pp)**
     - ``GetGlobalClusterPool()``
     - Distributes tasks to a ``pp`` cluster; intended for multi-machine workloads.

All backends share the same API so task code is backend-agnostic:

.. code-block:: python

    import nornir_pools as pools

    def compute(x, y):
        return x + y

    pool = pools.GetGlobalThreadPool()      # swap for any backend
    task = pool.add_task("label", compute, 3, y=5)
    result = task.wait_return()

Installation
------------

Install from Git (see also the package ``README.md``)::

  pip install git+https://github.com/nornir/nornir-pools.git --upgrade

Profiling output path
---------------------

Set ``NORNIR_PROFILE`` to enable multiprocess profiling output:

* If ``NORNIR_PROFILE`` is a valid filesystem path (or can be created), that directory is used.
* If it is set but invalid, the library may fall back to a default temporary directory.
* If unset, profiling output for this mechanism is not enabled.

Usage sketch
------------

Example: run a function on a thread pool::

   def add(x, y):
       return x + y

   import nornir_pools as pools
   thread_pool = pools.GetGlobalThreadPool()
   task = thread_pool.add_task("Add 3 + 5", add, 3, y=5)
   result = task.wait_return()
   print(result)

Cluster pool usage follows the same pattern with ``GetGlobalClusterPool()``::

   def add(x, y):
       return x + y

   import nornir_pools as pools
   cluster_pool = pools.GetGlobalClusterPool()
   task = cluster_pool.add_task("Add 3 + 5", add, 3, y=5)
   result = task.wait_return()
   print(result)

**API reference**

* :doc:`../api/nornir_pools`

Pool lifecycle and stage boundaries
-----------------------------------

Pipelines enqueue work on global thread- and process-backed pools across many stages.
**Waiting** for tasks and **closing** pools are separate:

* **Wait** — block until queued tasks finish; pools stay registered.
* **Close** — shut down workers and unregister the pool.

Thread-kind pools (``GetGlobalThreadPool``, subprocess ``GetGlobalProcessPool``,
``GetGlobalSerialPool``) run inside the parent process.  Process-kind pools
(``GetGlobalMultithreadingPool`` / ``GetLocalMachinePool``,
``GetGlobalClusterPool``) keep OS worker processes alive.  Spawning workers is
expensive, so production code keeps process pools warm between stages and recycles
thread pools at stage boundaries.

Recommended pattern at the end of each pipeline stage::

   import nornir_pools

   nornir_pools.ReleaseStagePools()

``ReleaseStagePools``:

1. Waits for **all** pool tasks (thread and process) so stage outputs are safe.
2. Shuts down **thread-kind** pools only.
3. Leaves **process-kind** pools registered for the next stage.

Use ``WaitOnAllPools()`` when you only need synchronization and will enqueue more
work immediately.  Use ``ClosePools()`` once at process exit or test teardown for
full shutdown.  Finer-grained helpers (``WaitOnThreadPools``,
``WaitOnProcessPools``, ``CloseThreadPools``, ``CloseProcessPools``) exist for
custom orchestration; see the API reference.

Set ``NORNIR_POOL_DIAG=1`` to log pool names, kinds, and active task counts on each
lifecycle call.  ``NORNIR_KEEP_PROCESS_POOLS=1`` skips process-pool shutdown in
``CloseProcessPools`` (normally unnecessary when using ``ReleaseStagePools``).

Which pool for which work
-------------------------

* **Python callables (CPU):** ``GetGlobalMultiprocessPool`` / local machine pool.
* **Python callables (I/O / light):** ``GetGlobalThreadPool``.
* **Shell / external binaries:** subprocess ``GetGlobalProcessPool`` —
  ``add_task`` expects a command string (or process args), not a Python callable.
* **Remote cluster callables:** ``GetGlobalClusterPool`` (Parallel Python).

Every ``add_*`` returns a Task; shutdown and stage boundaries must drain waits
(``ReleaseStagePools`` / ``WaitOnAllPools`` / ``ClosePools``).

Parallel Python callback timeout
--------------------------------

If the remote callback never fires after ``server.wait``, ``CTask.wait`` uses a
bounded secondary timeout (default 60s after the 300s primary wait), then
**unwinds** ``ActiveJobCount`` once and raises ``RuntimeError`` instead of
blocking forever. See the package ``README.md`` and
``tests/test_parallelpython_callback_timeout.py``.
