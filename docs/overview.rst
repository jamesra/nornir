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

Volume images frequently exceed reasonable sizes for single files. **Viking** is another Marc Lab tool for viewing and annotating huge datasets. Nornir output can be viewed with Viking when placed on a web server.

.. _Viking: https://connectomes.utah.edu/

System notes
------------

* 64-bit OS (development has focused on Windows).
* Rough guideline: about 2 GB RAM per CPU core for heavy pipelines (workload-dependent).

Terminology (short glossary)
----------------------------

**Block** — plastic-embedded sample before sectioning.

**Section / slice** — one thin physical slice from the block, typically tens of nanometres thick for TEM.

**Mosaic** — a set of overlapping microscope images covering an area larger than one field of view.

**Tile** — one image in a mosaic (with deliberate overlap between neighbors).

**Slice-to-slice (STOS)** — transforms that align one section's image to an adjacent section.

**Center section** — the section chosen as the origin of the volume coordinate system; other sections map toward it through composed transforms.

**Slice-to-volume** — the composed mapping from a section's mosaic space into the unified volume space.

For the same terms in the context of the full alignment walkthrough, see :doc:`overview_alignment_theory`.
