Production envelope
====================

Size production runs against this profile. It is an operator guideline, not a quota the software enforces.

* Volumes are very large, on the order of 100 TB, and usually live on a NAS.
* The path to that storage is often about 10 Gbps. Treat it as high latency. Prefer sequential reads, fewer round trips, and bounded concurrency. Do not assume local-disk latency for paths on the volume root.
* When hot data must leave the NAS, stage it on local SSD under ``/tmp`` (or the configured Nornir temp root). Budget 512 GB to 1 TB of scratch when the algorithm needs a large local cache. Do not assume ``/tmp`` is unlimited.
* Plan on about 2 GB of RAM per CPU core, sometimes about 3 GB per core. Size pools so the working set fits. Heavy paging is a failure mode for hot loops, even when the page file is on SSD.
* Typical GPUs are Ada RTX 4500 class or better. A GPU path still has to pay for host-to-device copies. See :doc:`gpu`.
* Containers that assemble tiles on CIFS set ``nofile`` to 65536. See :doc:`../docker/remote_deployment`.

Before adding a new parallel stage, check four things: it does not issue a storm of small NAS reads; any ``/tmp`` use states how much disk it needs; worker count times working set fits the RAM guideline; a GPU version is faster after transfer cost, not only in a device-only timer.
