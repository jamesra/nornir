Pools
=====

``nornir_pools`` runs the same task API on threads, processes, subprocesses, or a cluster. Every ``add_task`` returns a task. Call ``wait_return`` (or drain the pool) so failures are not dropped.

Which function
--------------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Work
     - Call
   * - Python callable, I/O or light CPU
     - ``GetGlobalThreadPool``
   * - Python callable, CPU
     - ``GetGlobalLocalMachinePool`` (threads and processes) or ``GetGlobalMultithreadingPool`` (processes, bypasses the GIL)
   * - One task at a time on a thread
     - ``GetGlobalSerialPool``
   * - Shell command or external binary
     - ``GetGlobalProcessPool``. Pass a command string, not a Python callable.
   * - Remote cluster
     - ``GetGlobalClusterPool``. If Parallel Python is not installed, this returns the local-machine pool.

There is no ``GetGlobalMultiprocessPool``.

Stage boundaries
----------------

Waiting and closing are different. Wait blocks until queued work finishes and leaves the pool registered. Close shuts workers down and unregisters the pool.

Thread-kind pools (``GetGlobalThreadPool``, ``GetGlobalProcessPool``, ``GetGlobalSerialPool``) live in the parent process. Process-kind pools (``GetGlobalMultithreadingPool``, ``GetGlobalLocalMachinePool``, ``GetGlobalClusterPool``) keep OS workers alive. Spawning those workers is expensive, so production code keeps them warm across stages and recycles thread pools at the boundary.

At the end of a pipeline stage::

   import nornir_pools
   nornir_pools.ReleaseStagePools()

``ReleaseStagePools`` waits for every pool, shuts down thread-kind pools, and leaves process-kind pools registered. Use ``WaitOnAllPools`` when more work will be queued immediately. Use ``ClosePools`` once, at process exit or test teardown.

``NORNIR_POOL_DIAG=1`` logs pool name, kind, and active task count on each lifecycle call.

If a Parallel Python callback never arrives, ``CTask.wait`` stops after a primary wait (default 300 seconds) and a secondary bound (default 60 seconds), unwinds the active job count once, and raises ``RuntimeError``.
