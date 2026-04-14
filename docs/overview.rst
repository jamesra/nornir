Overview
========

Nornir is a collection of Python packages for building image mosaics and 3D volumes from serial-section imaging data. Components cover thread/process pools, shared utilities, image registration, and volume construction.

**Documentation convention:** narrative and API reference for the umbrella project live in this monodoc. Each ``nornir-*`` package also has a short ``README.md`` at its repository root with an introduction and links back here.

Related tools
-------------

* **Viking** — viewing and annotating very large volumes; Nornir output can be served for Viking when placed on a web server.

System notes
------------

* 64-bit OS (development has focused on Windows).
* Rough guideline: about 2GB RAM per CPU core for heavy pipelines (workload-dependent).
