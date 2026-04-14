nornir-pools
============

Thread, process, and cluster **pool** abstractions so the same task code can run locally or on a cluster where supported.

This section consolidates the former standalone **Nornir Pools** doc tree.

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

Cluster pool usage follows the same pattern with ``GetGlobalClusterPool()``.

**API reference**

* :doc:`../api/nornir_pools`
