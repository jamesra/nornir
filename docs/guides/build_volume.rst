Build a volume
===============

The science behind each stage is in :doc:`../overview_alignment_theory`. The lab commands, with the flags the TEM scripts actually pass, are in :doc:`tem_scripts`. This page is the order of the work, not a second recipe. Host sizing is in :doc:`../host_requirements`. Deploy the machine that runs the scripts with :doc:`deploy_build_container`.

#. Import. For SerialEM that is ``TEMImport`` (``ImportIDoc``). ``VolumeData.xml`` is written at several levels of the tree, not only at the volume root. Those paths are on :doc:`../packages/nornir_buildmanager`.
#. Build each mosaic with ``TEMBuild``: prune, histogram, contrast, tile layout, image pyramids, a mosaic report, and a mosaic VikingXML file.
#. Align sections with ``TEMAlign``: blob filter, brute-force slice-to-slice, grid refine, slice-to-volume, then a VikingXML file whose StosGroup names show up in Viking. A bad brute-force pair is fixed in Pyre (:doc:`pyre_use`) before the later grid passes are treated as final.
#. View and annotate in `Viking <https://github.com/connectomes/Viking>`_. Analyze those annotations in `SBFSEM-tools <https://github.com/neitzlab/SBFSEM-tools>`_.

``nornir-build <Pipeline> --help`` lists flags for one stage. The grouped names are :doc:`../pipelines`. Those help examples are not the TEM script.
