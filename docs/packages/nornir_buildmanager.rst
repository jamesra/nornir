nornir-buildmanager
===================

Scripts and libraries for **constructing 3D volumes** from 2D image sets using the Nornir stack.

* **Python import:** ``nornir_buildmanager``
* **CLI entrypoint:** ``nornir-build``

**API reference**

* :doc:`../api/nornir_buildmanager`

Common workflow
---------------

1. Import data (for example ``ImportIDoc``, ``ImportDM4``, or ``ImportPMG``).
2. Clean input tiles with ``Prune`` and produce image histograms.
3. Register sections with ``Mosaic`` and downstream alignment pipelines.
4. Export manifests with ``CreateVikingXML`` when ready for consumption.

VikingXML Version 2
-------------------

``CreateVikingXML`` emits ``Volume/@Version="2"`` with a nested layout:

* All ``Section`` elements live under a single ``Sections`` wrapper.
* Each requested ``-StosGroup`` becomes a ``StosGroup`` element (``Name`` is the
  File → Transform → SliceToVolume menu label in Viking). Nested ``stos``
  children list individual transforms and omit redundant ``GroupName``.
* ``CreateVikingXML`` writes ``{Block.Path}/{Name}.zip`` containing the
  StosMap-selected ``.stos`` files (not every file under the group directory)
  as members at the archive root (basename only, no subfolders). It sets
  ``StosGroup/@zip`` to that volume-relative path (parent Block path included,
  e.g. ``TEM/SliceToVolume1.zip``). Nested ``stos/@path`` values use the same
  basename so they match zip entries. Rewrite is skipped when the zip's mtime
  and member set already match those transforms. Viking should GET the zip once
  and fall back to each child's ``path`` for any ``.stos`` missing from the
  archive (same pattern as the older volume-level ``StosZip`` attribute).

Example::

    <Volume Version="2" Name="..." num_stos="N" num_sections="M" InputChecksum="...">
      <Sections>
        <Section Number="1" Path="..." Name="...">...</Section>
      </Sections>
      <StosGroup Name="SliceToVolume1" zip="TEM/SliceToVolume1.zip">
        <stos controlSection="645" mappedSection="1" path="1-645.stos"
              pixelspacing="1" type="Grid"/>
      </StosGroup>
    </Volume>
