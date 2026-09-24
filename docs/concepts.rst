Concepts
========

:doc:`overview` states what Nornir is for. :doc:`overview_alignment_theory` walks through mosaic capture, slice-to-slice registration, and slice-to-volume mapping, and names the ``nornir-build`` command for each stage.

Glossary
--------

**Block**
    Plastic-embedded sample before sectioning. In the volume tree, a block groups sections and is the unit of batch processing.

**Section / slice**
    One thin physical slice from the block, typically tens of nanometres thick for TEM. One Z level in the volume.

**Channel**
    A named image set on a section, such as ``TEM`` or a derived filter stack.

**Filter**
    An image-processing product of a channel (raw tiles, leveled tiles, a blob image). Pipelines select filters by name.

**Tile**
    One microscope image in a mosaic. Neighbors overlap on purpose.

**Mosaic**
    The set of tiles that covers an area larger than one field of view, plus the transform that lays them out. Stored as a ``.mosaic`` file.

**Pyramid level**
    A downsampled copy of a tile or assembled image. Lower levels are smaller and are what registration usually measures.

**Prune**
    Drop tiles that do not have enough texture to align. The ``Prune`` pipeline does this before ``Mosaic``.

**Slice-to-slice (STOS)**
    A transform that aligns one section to an adjacent section. Stored as a ``.stos`` file.

**Blob**
    A texture filter that keeps features visible after downsampling. ``CreateBlobFilter`` builds it. TEM brute alignment uses it.

**Grid / mesh**
    After a rigid or translation step, a grid of cells is measured and the mesh records a local offset at each cell. Mosaic refine and slice-to-slice refine both do this. In Pyre, a refined grid does not support adding or deleting control points the way a triangulation transform does.

**Center section**
    The section chosen as the origin of the volume coordinate system. Other sections map toward it.

**Slice-to-volume**
    The composed mapping from a section's mosaic space into that shared volume space. ``SliceToVolume`` builds it from the slice-to-slice chain.

**VikingXML**
    The manifest ``CreateVikingXML`` writes so Viking can open the volume. The ``StosGroup`` name is the label in Viking's transform menu.
