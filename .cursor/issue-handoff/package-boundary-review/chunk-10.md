# Chunk 10 — volumemanager and pipeline orchestration

## Findings

- Volumemanager owns `VolumeData.xml`, dirty flags, and node identity. Pipeline stages yield nodes for `_SaveNodes`. That is the package purpose. No pixel algorithms turned up that should move.
- Segmentation stages are reached from pipeline XML (`segmentationtraining.IngestGeometries`, `ExportSectionCrops`, `RepairAnnotationOverlays`, `CleanupAnnotationCrops`) and from `segmentationtraining/__init__.py`. The init import is what forces the gallery stub. Orchestration can keep those names; the leaf modules they call should import without executing this package init.

## Carry forward

Package init import fan-out.
