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
