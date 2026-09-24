Overview
========

Nornir is a collection of Python packages for building image mosaics and 3D volumes from serial-section imaging data. Components cover thread/process pools, shared utilities, image registration, and volume construction.

Mission
-------

Nornir's goal is to take large sets of overlapping images in 2D and 3D and produce **registered** (aligned) 2D and 3D volumes at any practical size and scale.

**Theory and figures:** for a guided walkthrough of mosaic capture, tile alignment, slice-to-slice registration, and volume mapping—with the original figures from the public manual—see :doc:`overview_alignment_theory`.

**Documentation convention:** narrative and API reference for the umbrella project live in this monodoc. Each ``nornir-*`` package also has a short ``README.md`` at its repository root with an introduction and links back here.

History
-------

Nornir evolved from a collaboration between the `Marc Lab`_ and the `Scientific Computing Institute`_ (Tasdizen and Whitaker groups) at the University of Utah. The original tools, known as the `NCR Toolset`_, were used to construct `RC1`_, a 250 µm diameter, 33 µm tall cylinder of rabbit retina at a resolution of 2.18 nm/pixel.

Nornir is a work in progress. It supports importing images from transmission electron microscopes running SerialEM (``.idoc`` files), light microscopes running Surveyor (``.pmg`` files), and other volumes represented with a single image per section (``.png`` files).

.. _Marc Lab: https://prometheus.med.utah.edu/~marclab/marclab_09_science-papers.html
.. _Scientific Computing Institute: https://www.ucnia.org/
.. _NCR Toolset: https://www.ucnia.org/download/ncrtoolset/
.. _RC1: https://pubmed.ncbi.nlm.nih.gov/21311605/

Related tools
-------------

Nornir builds the aligned volume and a VikingXML manifest. **Viking** views and annotates that volume. **SBFSEM-tools** analyzes Viking annotations in MATLAB. Build in Nornir, view and annotate in Viking, analyze in SBFSEM-tools.

* `Viking <https://github.com/connectomes/Viking>`_
* `SBFSEM-tools <https://github.com/neitzlab/SBFSEM-tools>`_

See :doc:`guides/build_volume`.

System notes
------------

What a machine needs to run Pyre, a workstation pipeline, or Docker is in :doc:`host_requirements`. Production volumes (NAS, scratch disk, GPU class) are in :doc:`performance/envelope`.

Terminology
-----------

Terms used across the manual (block, section, mosaic, tile, channel, filter, prune, blob, STOS, grid, slice-to-volume) are defined in :doc:`concepts`.
