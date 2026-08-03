nornir-imageregistration
========================

Core **image registration** algorithms for aligning 2D images into larger mosaics and 3D volumes.

Conceptual background (mosaics, phase correlation, slice-to-slice refinement, volume mapping) is in :doc:`../overview_alignment_theory`.

* **Python import:** ``nornir_imageregistration``

Optional GPU extras (see package ``README.md``) are not required for the CPU code paths.

**STOS image paths**

``StosFile.Save`` stores control/mapped image and mask paths **relative to the
``.stos`` directory** when a relative form is expressible. ``StosFile.Load``
resolves those lines back to absolute paths in memory. When the image and
``.stos`` locations do not share a common root (cross-drive on Windows, or
incompatible UNC shares), Save falls back to an absolute path and logs a
warning — there is no portable relative encoding across those boundaries.
Use Pyre path replacement / volume reroot when moving trees between machines.

**API reference**

* :doc:`../api/nornir_imageregistration`
