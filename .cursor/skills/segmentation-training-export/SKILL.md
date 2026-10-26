---
name: segmentation-training-export
description: >-
  Run, change or debug the ExportTrainingData pipeline (SAM2 annotation crops, masks,
  circle_annotations.json, shapes.jsonl, training_set.json) in nornir-buildmanager
  segmentationtraining. Use when exporting or refreshing a training set, choosing between
  -Update, -RefreshOData, -Force and a new set number, exporting another lab's volume
  with -VikingXML, touching Viking OData ingest or paging, or checking what the
  Sam2Trainer repo consumes.
---

# Segmentation training export

- Code: `nornir-buildmanager/nornir_buildmanager/operations/segmentationtraining/`.
- Pipeline and every flag's help text: `nornir-buildmanager/nornir_buildmanager/config/Pipelines.xml` (`<Pipeline Name="ExportTrainingData">`).
- Set naming and the `training_set.json` sidecar: [Training-set-naming](../../rules/Training-set-naming.mdc) (not repeated here). Read it before passing `-SetVersion` or copying an export into a set.

## Pipeline steps (in order)

| Step | Module | Does |
|------|--------|------|
| `CheckTrainingSet` | `training_set.py` | Refuses a bad `-SetVersion` or changed creation rules. Writes nothing. |
| `IngestGeometries` | `ingest.py` via `pipeline.py` | OData or `-Geometries` dump into per-section spills in the work folder. Skipped by `-Cleanup` and `-Repair`. |
| `ExportSectionCrops` | `pipeline.py`, `planning.py`, `stitch.py`, `masks.py`, `update.py` | Per local section (Channel/Filter regex): plan, stitch crops, rasterize masks, write JSON. |
| `ExportRemoteSections` | `pipeline.py`, `remote_tiles.py` | Same, with tiles fetched through `-VikingXML`. No-op without it. |
| `CleanupAnnotationCrops` | `cleanup.py` | Audit and repair corrupt products. Only with `-Cleanup`. |
| `WriteCircleAnnotations` | `circles.py` | Rebuilds `circle_annotations.json` from the manifest every run. |
| `WriteLocationShapes` | `shapes.py` | Rebuilds `shapes.jsonl` and manifest `structureIds` / `linkedIds` every run. |
| `WriteGallery` | `sam2/__init__.py`, `catalog.py` | Applies `ignore.json` moves, rebuilds `annotation_crops.sqlite`. |
| `WriteTrainingSetInfo` | `training_set.py` | Writes `training_set.json` last, atomically. |

## What it writes

`-Output` holds only what the trainer reads, so it can be copied into a set unchanged.

| Path under `-Output` | Content |
|----------------------|---------|
| `manifest.jsonl` | One row per crop: `image`, `json`, `imageKey`, `locationIds`, `structureIds`, `linkedIds`, `downsample`, `volume`, `z`. |
| `images/{imageKey}.png` + `.json` | Lossless crop and its SA-1B JSON (COCO RLE per annotation, `image.odata`, `originX`/`originY`, `windowIndex`/`windowCount` for split masks). |
| `masks/{imageKey}_{locationId}.png` | 1-bit mask per annotation. Name format: `annotation_crops/maskname.py`. |
| `ignored/` + `ignore.json` | Masks moved aside by the gallery's reject list. |
| `overlays/parts/{locationId}.json` | Always written. QA `overlays/{imageKey}.png` only with `-Overlay` (the gallery draws its own). |
| `circle_annotations.json` | Version 1, `diameter_scale` 1.0, `grid_cells` keyed by `imageKey`: `location_id`, `center_x`, `center_y`, `radius`, `structure_label`, `has_polygon_mask`, `source` (`annotated` or `inscribed`). Crop pixels at the crop's downsample, y down, unclipped. |
| `shapes.jsonl` | One line per polygon location with a mask or a link: `structure_id`, `has_mask`, `centroid`, `area` (D1 mosaic px), `polygons` relative to the centroid, `linked` `[location_id, z]` within 2 sections on the same structure. |
| `source.json` | Provenance: `kind`, `odata`, `filter`, `exporter`, `ingestedAt`, and `tiles` for remote exports. Never a SQL connection. |
| `annotation_crops.sqlite` | Gallery catalog. |
| `training_set.json` | Set sidecar (see the rule). |

`imageKey` ends in `_D{ds}_X{x0}-{x1}_Y{y0}-{y1}` in crop pixels; origins can be negative (`X-512-512`). No negatives folder: the trainer builds negatives (`annotation_crops/negatives.py` in Sam2Trainer).

The re-run cache is beside the output, not in it: `../_work_cache/<output folder name>/` (`workdir.py`), holding `section_{z}.jsonl`, `circles_{z}.jsonl`, `cache.meta.json`, section watermarks `section_{z}.meta.json`, RLE sidecars `rle/`, `location_links.json` and `remote_tiles/`. Do not copy it into a set or delete it before an `-Update`.

## Run it

`nornir-build` (entry point `nornir_buildmanager.build:Execute`; same as `python -m nornir_buildmanager`). Global flags go before the volume path.

```powershell
# New set from a local volume
venv\pyre314\Scripts\nornir-build.exe -computational_library numpy /storage4/RPC3 ExportTrainingData `
  -OData https://websvc.codepharm.net/RPC3/OData -Output Y:/SAM2TrainingData/TEM/v4/RPC3 `
  -SetVersion v4 -Channels TEM -Filters Leveled -StructureTypeId 1,3 -Workers 16 -MaskWorkers 8

# Another lab's volume (local folder may be empty); later runs add -Update
venv\pyre314\Scripts\nornir-build.exe -computational_library numpy /storage4/CPED ExportTrainingData `
  -VikingXML http://v2223.host.s.uw.edu/Neitz/CPED/cped.xml -OData https://websvc.codepharm.net/NeitzCPED/OData `
  -Output Y:/SAM2TrainingData/SEM/v1/CPED -SetVersion v1 -Channels SEM -Filters Leveled -StructureTypeId 1,3 -Update
```

| Flag | Meaning |
|------|---------|
| `-OData` / `-Geometries` | Exactly one is required on every exporting run, `-Update` included. Ingest does not read the OData root back from `source.json`. |
| `-ODataFilter` | Replaces `$filter`; `-StructureTypeId` is then ignored. |
| `-StructureTypeId` | Exact `Parent/TypeID` list (`1,3`); no subtype expansion. Omitted: Cell plus subtypes. |
| `-Output` | Default `<volume>/AnnotationCrops` (`build.py` `_DEFAULT_OUTPUT_FOLDER`). |
| `-Channels`, `-Filters` | Regex for the tileset's channel and filter. Defaults `TEM`, `Leveled`. |
| `-Downsample`, `-Exporter`, `-Pad`, `-MaxTexture`, `-MinProcessPixels`, `-IncludeOffEdge` | Creation rules: define a sample, fingerprinted in the sidecar, in the crop watermark hash. Defaults 1, `tiled`, 1, 1024, 16, off. |
| `-MaxTiles`, `-Workers`, `-MaskWorkers`, `-StageTiles`, `-Overlay`, `-FailMissingTileset` | Run-time only. |
| `-Sections` | Section subset (`1,3,5-7`). Omitted: every Z with geometries. |
| `-VolumeName` | Name in manifest and keys. Default: VikingXML `Name`, else the OData database name. In the watermark hash, so changing it restitches everything. |
| `-VikingXML`, `-TileHost`, `-TileCache`, `-TileRevalidate` | Remote tiles. `-TileRevalidate`: `once` (default), `always`, `never`, or hours. |
| `-Update` | ID-set delta (below). Not with `-Force`. |
| `-RefreshOData` | Refetch MosaicShape for every section, then remask; restitch only where windows moved. |
| `-Force` | Refetch and restitch everything. |
| `-Repair` | Restitch only crop PNGs missing from `images/`. No OData. Not with `-Force`, `-Update`, `-RefreshOData`, `-Cleanup`. |
| `-Cleanup` | Audit and repair corrupt products. No ingest, no stitch. |
| `-SetVersion`, `-ParentSet`, `-SetDescription` | Sidecar fields; see the rule. |

Launch configs (`.vscode/launch.json`; all set `NORNIR_HEADLESS=1` and MQTT dashboard env):

| Config | Output root | Notes |
|--------|-------------|-------|
| `ExportTrainingData (OData)` | `//192.168.0.199/Data/SAM2TrainingData/TEM/<trainingSetVersion>/<volume>` | Debug, `-debug`, `-SetVersion` from the `trainingSetVersion` input (default `v4`). |
| `ExportTrainingData (OData) run` | same | `-Update -RefreshOData`, `-StructureTypeId 1`. |
| `ExportTrainingData (OData) run legacy` | `.../TEM/<legacySetFolder>/<volume>` | `-Exporter legacy -Update`, no `-SetVersion` (folder name `legacy` is not a set name). |
| `ExportTrainingData (TemporalMonkey2 / InferiorMonkey / CPED / NasalMonkey, remote VikingXML)` | `Y:/SAM2TrainingData/SEM/v1/<volume>` | `-Channels SEM -Update`, no `-SetVersion`. |

`.vscode/tasks.json` task `ExportTrainingData (OData) run` writes to `<volumesRoot>/<volume>/AnnotationCrops`. `Y:` and `//192.168.0.199/Data` are the same share. Do not run any of these against the live servers from an agent.

## Update, refresh, re-export or new set

Ingest is two-phase (`ingest.iter_odata_locations`): pass A pulls `ID,Z,LastModified,ParentID,OffEdge` for all locations; pass B pulls MosaicShape only for sections whose ID set or any `LastModified` changed (all sections with `-RefreshOData` or `-Force`). Circles are refetched on every OData ingest. Crop freshness (`freshness.py`) compares the section watermark: ID set, max `LastModified`, the `ExportParams` hash and the tileset mtime.

| Situation | Run |
|-----------|-----|
| Annotations added, deleted or edited | `-Update`. Deleted locations lose masks and membership; added ones merge into an existing crop or get a new one; survivors with a changed `LastModified` are remasked in place. Other crops are untouched. |
| Suspect edits did not bump `LastModified`, or links look stale | `-Update -RefreshOData`. |
| Tiles rebuilt locally (new tileset level mtime) | Plain run: affected crops restitch on their own. |
| Crop PNGs deleted or lost in a copy | `-Repair`. |
| Corrupt or half-written products | `-Cleanup`. |
| Any creation rule changes (pad, downsample, exporter, max texture, filter, structure types, channels, off-edge) | New set number in a new folder (`-SetVersion v5`). `CheckTrainingSet` refuses the same number. |
| Exporter output changed (new file or field) | `-Update` on the export folder: `circle_annotations.json`, `shapes.jsonl` and manifest link fields rebuild every run without restitching. A published set is immutable, so the result is a revision (`v3.1`), or a new set if what a sample is changed. |
| Nothing else works | `-Force` (full refetch and restitch; hours per volume). |

`shapes.jsonl` links come from one pull (`$expand=LocationLinksA,LocationLinksB` on the export's own Locations filter), cached in `location_links.json`, repeated with `-Update`, `-RefreshOData`, `-Force`, or when the location set changes.

## Data faithfulness

The exporter writes true geometry; scaling, jitter and augmentation belong to the trainer.

- Circle radii are true; `diameter_scale` stays 1.0 so consumers can tell these files from old ones that baked in 0.8. Do not add a scale flag (`-CircleDiameterScale` was removed). The trainer applies `prompt.circle_diameter_scale` (0.95) in `sam2_segmentation_trainer/config/em_finetune.yaml`.
- `radius` is the OData `Radius` in D1 mosaic pixels. Inscribed circles are the largest circle inside the exterior ring (distance transform), not the centroid.
- Windows over the mosaic edge keep their negative origin in the key and in `originX`/`originY`. Never clamp them.
- Centers and radii are never clipped to the crop.

## Viking OData

- The server root comes only from `-OData` (launch configs use `https://websvc.codepharm.net/<db>/OData`), recorded in `source.json` and each crop JSON for consumers. Requests send no credentials.
- The server caps every page at 16384 rows and sends no `@odata.nextLink`. `ingest._iter_odata_documents` follows a nextLink when present, else continues with `$skip` while a page is full (`>= $top`) or short of `@odata.count`. Every Locations query goes through `_odata_locations_url` (`$orderby=Z,ID`, `$count=true`, `$top=16384`). New queries must use `_iter_odata_pages` / `_fetch_odata_entities`, never a single GET.
- `$filter` is limited to 100 AST nodes (ASP.NET `MaxNodeCount`); Z subsets are chunked into `ge`/`le` runs under that budget (`_chunk_z_for_odata_filter`). A long `-ODataFilter` fails with a user error.
- 300 s socket timeout per blocking read (`ODATA_TIMEOUT_SECONDS`); a stall fails the run.

## Remote volumes (`-VikingXML`)

Tiles are fetched into `remote_tiles/`, validated cheapest first: VikingXML checksum or ETag, then the level's directory listing, then a conditional GET per tile (`remote_tiles.py` docstring). Only tiles under planned crops are fetched. Sections come from the ingest, limited to those with a matching VikingXML Channel.Filter.

## Tests

From the repo root (all synthetic, headless, about 1200 tests in under 3 minutes; no markers, no external data):

```powershell
$env:NORNIR_HEADLESS='1'
venv\pyre314\Scripts\pytest.exe nornir-buildmanager/tests/operations -k "segmentationtraining or segtrain" `
  -m "not graphical and not slow and not gpu and not needs_data"
```

- Files: `tests/operations/test_segmentationtraining*.py`, `test_segtrain_*.py`, `tests/pipeline/test_build_early_meta.py`.
- Fixtures are built in `tmp_path`. OData is faked by injecting `http_get` (`_getter` / `_entity` in `test_segmentationtraining.py`); paging and `$skip`: `test_segtrain_ingest_helpers.py`, `test_segmentationtraining_shapes.py`. Remote HTTP uses a loopback server (`test_segtrain_remote_http_get.py`, `test_segmentationtraining_remote.py`).
- Several tests parse `Pipelines.xml` (defaults must match `training_set.creation_rules`, step order, declared arguments): changing a flag or default means updating both.
- Changes to crop placement, masks or coordinates fall under [Stable-path-output-parity](../../rules/Stable-path-output-parity.mdc): compare outputs before and after.

## Trainer handoff

Current trainer: `D:\src\git\Sam2Trainer` (outside this workspace; GitHub `jamesra/Sam2SegmentationTrainer`, active 2026-10-26). `D:\src\git\VikingSlackUsersAI\Sam2SegmentationTrainer` is an older clone (last commit 2026-10-13); `D:\src\git\Sam2SegmentationTrainer` is not a git repository. Do not edit either from here.

| Trainer reads | Where to check compatibility (Sam2Trainer) |
|---------------|-------------------------------------------|
| `manifest.jsonl`, `images/`, `masks/`, `ignore.json` | `sam2_segmentation_trainer/data/manifest.py`, `paths.py` (flat `<vol>/manifest.jsonl` wins over `<vol>/AnnotationCrops/`) |
| `circle_annotations.json` | `data/tiles.py`, `data/prompts.py`, `config/em_finetune.yaml` |
| `shapes.jsonl` | `data/shapes.py`, `data/projection.py` (adjacent-section seed) |
| `source.json` `annotationDb` | `annotation-gallery` grants; `scripts/NAS/backfill-annotation-db` |
| `training_set.json` | Not read yet (see the rule's Status) |
| Folder names `images`, `masks`, `ignored`, `overlays` | Must not change (`product_index.py`) |

`annotation_crops/` (mask names, RLE, `ignore.json`, score table) is vendored in both repos, "keep identical" in its docstring, but has drifted: Sam2Trainer adds `negatives.py`, `prompt_encoding.py`, `card_scores.py`, a faster `rle.bbox_area_from_rle` and a superseding trigger in `scores.py`. Diff both trees before changing a shared format.

## Open gaps (verified in code 2026-10-26; delete each when done)

- Every exporting run rewrites `source.json` from the ingest meta (`ingest.write_export_source`), keeping only `exporter` (and `odata` for SQL), so a backfilled `annotationDb` is dropped; `training_set.json` `source` is rebuilt from the arguments the same way. The exporter does not write `annotationDb` itself, and SEM folders depend on it for gallery grants.
- SEM launch configs pass no `-SetVersion`: `SEM/v1/CPED/training_set.json` has `set_version: null` in folder `v1`; TEM `v3/RC2` has null too, and `v3/RC1`, `v3/RPC1`, `v3/RPC2` have no sidecar.
- TEM `v3` `RC1` and `RPC1` `shapes.jsonl` are dated 2026-10-14 (before the paging fix) and stop at z 282 and z 742; 2652 and 24702 manifest locations have no shape. The manifests are complete.
- Circle centres use the circumcentre of three `CIRCULARSTRING` points (`circles.py`); the OData circle query does not select `X`, `Y`. The trainer rule `circle-centre-xy.mdc` asks for `X`, `Y` (measured agreement 0.005 px on RC1).
- Remote sections pass no tileset mtime, so a remote tile change is picked up only when its crop is rebuilt for another reason (`-Force`, new or moved windows). Other labs' servers' directory listing and ETag support is unverified beyond the SEM v1 exports.
- No skip list for confirmed-bad circles; Sam2Trainer `scripts/circle_review.py` only writes CSVs.
- One downsample per export: no D2/D4 multi-scale tiles.
