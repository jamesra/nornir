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
