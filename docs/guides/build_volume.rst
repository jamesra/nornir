Build a volume
===============

``nornir-build`` runs one named pipeline against a volume directory. The science behind each stage is in :doc:`../overview_alignment_theory`. Flags below are the examples already shipped in ``Pipelines.xml`` and the buildmanager README. Run ``nornir-build <Pipeline> --help`` before changing them. Host sizing is in :doc:`../host_requirements`.

Import
------

Pick the importer that matches the microscope:

* SerialEM ``.idoc``::

     nornir-build ImportIDoc /data/volume /data/idoc -Sections 1-10 -CameraBpp 14

* Digital Micrograph ``.dm4``::

     nornir-build ImportDM4 /data/volume /data/dm4 -Sections 1-20 -overlap 10,20

* Surveyor ``.pmg``::

     nornir-build ImportPMG /data/volume /data/pmg -Scale 4.0

``VolumeData.xml`` is written at several levels of the tree (volume, block, section, channel), not only at the volume root. The locations are on :doc:`../packages/nornir_buildmanager`.

Prune and mosaic
----------------

``Prune`` drops tiles that do not have enough texture. ``Mosaic`` then lays the remaining tiles out and writes an assembled mosaic.

::

   nornir-build Prune /data/volume -InputFilter Raw8 -DefaultThreshold 0.2 -Sections 1-10
   nornir-build Mosaic /data/volume -InputFilter Raw8 -InputTransform Prune -OutputTransform Grid -RegistrationDownsample 4

Slice-to-slice
--------------

``CreateBlobFilter`` builds the texture image used when downsampled TEM sections would otherwise lose features. ``AlignSections`` brute-force aligns adjacent sections and records a center section. ``RefineSectionAlignment`` applies the grid refine, often in passes at finer downsampling.

::

   nornir-build AlignSections /data/volume -Downsample 8 -Channels .* -Filters Raw8 -OutputStosMap PotentialRegistrationChain

This brute-force step is the usual place to open Pyre and correct a bad pair before refine. Controls are in :doc:`pyre_use`.

Slice-to-volume and export
--------------------------

``SliceToVolume`` composes the slice-to-slice chain into one transform per section onto the center section. ``Assemble`` builds images from a transform and a filter. ``CreateVikingXML`` writes the manifest Viking reads. The ``-StosGroup`` name is the label in Viking's File → Transform → SliceToVolume menu.

::

   nornir-build CreateVikingXML /data/volume -OutputFile MyVolume -StosMap FinalStosMap -StosGroup Grid32 -StosGroup SliceToVolume1

The Version 2 XML and zip layout is documented on :doc:`../packages/nornir_buildmanager`. Put the volume where Viking can read it.

View and analyze
----------------

Nornir stops at the VikingXML manifest and the image pyramids.

#. View and annotate the volume in `Viking <https://github.com/connectomes/Viking>`_.
#. Analyze those annotations in `SBFSEM-tools <https://github.com/neitzlab/SBFSEM-tools>`_ (MATLAB).

Build in Nornir, view and annotate in Viking, analyze in SBFSEM-tools.
