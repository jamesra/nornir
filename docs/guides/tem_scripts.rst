TEM build scripts
=================

Inside the build container (:doc:`deploy_build_container`) the lab sequence is three wrappers. Each one is a single ``nornir-build`` process. Stages run in order, joined by ``--then``, and the process stops on the first failure. The default compute library is CuPy (``NORNIR_COMPUTATIONAL_LIBRARY``). Progress is published to the co-located dashboard.

Run them in this order:

* ``TEMImport`` when the volume has not been imported.
* ``TEMBuild`` to build mosaics. It assumes ``VolumeData.xml`` already exists. ``TEMBuild-import`` is import plus the same mosaic stages.
* ``TEMAlign`` after the mosaics exist. It produces the slice-to-volume transforms Viking reads.

The science for these stages is :doc:`../overview_alignment_theory`. Flags below are the ones in ``nornir-buildmanager/scripts``. ``nornir-build <Pipeline> --help`` lists every flag; the pipeline catalogue (:doc:`../pipelines`) is not this recipe.

TEMImport
---------

``ImportIDoc`` copies a SerialEM ``.idoc`` directory into the volume and writes ``VolumeData.xml`` at the volume, block, section, and channel levels.

::

   TEMImport /path/to/idoc /path/to/volume

TEMBuild
--------

Same chain as the VS Code launch configuration "TEM Build: full sequence (sequential)". Pass the volume directory, or let the script prompt.

* ``Prune -InputFilter Raw8 -Downsample 4 -Channels TEM -DefaultThreshold 10.0`` — drop tiles that do not have enough texture to align.
* ``Histogram -Filters Raw8 -InputTransform Prune -Downsample 4 -Channels TEM`` — contrast statistics for the tiles that remain.
* ``AdjustContrast -InputFilter Raw8 -OutputFilter Leveled -InputTransform Prune -Channels TEM`` — write the ``Leveled`` filter that mosaic registration uses.
* ``Mosaic -InputFilter Leveled -RegistrationDownsample 4 -InputTransform Prune -OutputTransform Grid -Channels TEM`` — lay the tiles out. The output transform is ``Grid``.
* ``Assemble -Channels TEM -Filters Leveled -Downsample 8,16,32 -NoInterlace -Transform Grid`` — build pyramid images from that layout.
* ``MosaicReport -PruneFilter Raw8 -ContrastFilter Raw8 -AssembleFilter Leveled -AssembleDownsample 16 -Output MosaicReport`` — QA report for the mosaic.
* ``CreateVikingXML -OutputFile Mosaic`` — a mosaic manifest. This is not a slice-to-volume group yet.

TEMAlign
--------

Run this after TEMBuild. A bad brute-force pair is fixed in Pyre (:doc:`pyre_use`) before you treat the later grid passes as final.

* ``CreateBlobFilter -Channels TEM -InputFilter Leveled -Levels 16,32,64 -OutputFilter Blob -Radius 9 -Median 7 -Max 3`` — a texture image so downsampled brute force still sees features.
* ``AlignSections -NumAdjacentSections 1 -Filters Blob -UseMasks -Downsample 64 -Channels TEM`` — first slice-to-slice placement, one neighbor each way, and a potential registration chain.
* ``AssembleStosOverlays -StosGroup StosBrute -Downsample 64 -StosMap PotentialRegistrationChain`` — overlay pictures of those pairs.
* ``SelectBestRegistrationChain -StosGroup StosBrute -Downsample 64 -InputStosMap PotentialRegistrationChain -OutputStosMap FinalStosMap`` — choose the chain and write ``FinalStosMap``.
* ``RefineSectionAlignment -InputGroup StosBrute -InputDownsample 64 -OutputGroup Grid -OutputDownsample 32 -Filter Leveled`` — first grid refine, from the brute result at 64 to a grid at 32.
* ``AssembleStosOverlays -StosGroup Grid -Downsample 32 -StosMap FinalStosMap`` — overlays of that grid.
* ``CreateVikingXML -StosGroup Grid32 -StosMap FinalStosMap -OutputFile Grid32`` — publish that pass. ``Grid32`` is a StosGroup name Viking can show.
* ``RefineSectionAlignment -InputGroup Grid -InputDownsample 32 -OutputGroup Grid -OutputDownsample 16 -Filter Leveled`` — second grid refine, 32 to 16.
* ``SliceToVolume -Downsample 16 -InputGroup Grid -OutputGroup SliceToVolume -NoLinearBlend`` — one mapping per section onto the center section.
* ``ScaleVolumeTransforms -InputGroup SliceToVolume -InputDownsample 16 -OutputDownsample 1`` — scale that mapping to full resolution.
* ``LinearizeVolume -InputGroup SliceToVolume -InputDownsample 1 -OutputGroup SliceToVolumeLinear -min_blend 0.005 -max_blend 0.05 -travel_limit 512 -reblend_iterations 8 -reblend_tolerance 0.5`` — a blended variant of the same mapping.
* ``CreateVikingXML -OutputFile SliceToVolume -StosGroup SliceToVolume1 -StosGroup SliceToVolumeLinear1 -StosMap SliceToVolume`` — the Viking manifest. Those StosGroup names are the labels in Viking's File → Transform → SliceToVolume menu.
* ``MosaicToVolume -InputTransform Grid -OutputTransform ChannelToVolume -Channels '(?!Registered)'`` — map each mosaic channel into volume space.
* ``Assemble -Channels '(?!Registered)' -Filters Leveled -Downsample 32 -NoInterlace -Transform ChannelToVolume -ChannelPrefix Registered_`` — write ``Registered_*`` channels at downsample 32.
* ``MosaicReport -PruneFilter Raw8 -ContrastFilter Raw8 -AssembleFilter Leveled -AssembleDownsample 32 -Output VolumeReport`` — QA report for the volume.
* ``ExportImages -Channels Registered -Filters Leveled -Downsample 32`` — export the registered leveled images next to the volume.

View and annotate the result in `Viking <https://github.com/connectomes/Viking>`_. Analyze those annotations in `SBFSEM-tools <https://github.com/neitzlab/SBFSEM-tools>`_.
