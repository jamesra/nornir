Pipeline catalogue
==================

``nornir-build <Name> --help`` prints the flags for one pipeline. Definitions live in ``nornir-buildmanager/nornir_buildmanager/config/Pipelines.xml``. The walkthrough with copy-paste examples is :doc:`guides/build_volume`. This page only groups the stages a volume usually runs, in order.

Import
------

``ImportIDoc``, ``ImportDM4``, ``ImportPMG``, ``ImportMRC``, ``ImportImages``. ``AdoptVikingVolume`` adopts an existing Viking-layout tree; read its help before pointing it at a live volume.

Mosaic
------

``Prune``, ``Mosaic``. Contrast, shade, and histogram pipelines sit beside these and are optional.

Section alignment
-----------------

``CreateBlobFilter``, ``AlignSections``, ``RefineSectionAlignment``.

Volume and export
-----------------

``SliceToVolume``, ``Assemble``, ``CreateVikingXML``.

The XML file also defines maintenance pipelines (rename a filter, lock a transform, list cutoffs). Those are not part of the first-volume path.
