# Metadata port: XML to SQLite

Read by the scout and implementer on port wakes (Category 15). General gates: [gates.md](gates.md); the protected list in [protected.md](protected.md) still applies.

## Goal and strategy

Move Nornir volume metadata (today `VolumeData.xml` plus sharded `*_Link` files, owned by `nornir-buildmanager`) to SQLite by **dual-write with XML authoritative**: write SQLite alongside XML and check parity, then switch reads per volume behind a flag. Making SQLite the default reader and retiring XML writes are the user's decisions (stage 6), not the loop's.

Why staged: pipelines (`config/Pipelines.xml`, `PipelineManager`) query the tree with ElementTree XPath (`find`/`findall` on `Block/Section`, `Filter[@Name='...']/TilePyramid`), `XElementWrapper` subclasses `ElementTree.Element`, and nothing locks `VolumeData.xml` across processes. A one-step cutover would touch all of that at once.

## What exists today (verify before relying on it)

- Production path: `volumemanager/volumemanager.py` (`VolumeManager.Load`/`Save`/`SaveSingleFile`), `volumemanager/xcontainerelementwrapper.py` (`_load_link_element`, `_replace_links`, `Save`/`_Save`, `__SaveXML` with backup rotation), `xelementwrapper.py` (dirty flags, lazy `*_Link` resolve, `RLock`), and about 25 `*Node` types wrapped by `elementwrapping.WrapElement`. Dirty flags are per container; linked dirtiness does not bubble up.
- Parallel, **unwired** package: `nornir_buildmanager/metadata/` (`volume_metadata.py` `MetadataNode`/`VolumeMetadataBackend`, `xml_backend.py`, `sqlite_backend.py`, `migrate.py`, CLI `nornir-migrate-volume`), tested in `tests/test_metadata_migration.py`. Schema: a generic `nodes` plus `node_attribs` tree with `schema_info` versioning. A starting point, not a drop-in for pipelines: `save()` deletes and rewrites every row, `_compare_trees` is lenient about whitespace-only text, and connections use WAL unconditionally.
- Locking: `Lockable` is a logical `Locked` XML attribute, not an OS lock. In-process `RLock`s guard saves; there is no cross-process write lock.
- Other readers: `nornir-volumemodel` parses XML itself; `nornir-web` imports through an external package; the Viking client consumes the `Volume.VikingXML` export, which stays generated from the tree.

These files change; re-read them at the start of each port wake.

## Rules for every stage

- **XML remains the source of truth and its output stays byte-identical** until a stage-6 decision says otherwise. A stage that changes saved XML has failed.
- Each stage is one or more wakes of about 300 changed lines, leaves the tree working, and is opt-in behind an environment variable or argument defaulting to the old behavior.
- Read new environment variables in one place and document them in the buildmanager README. Log through `nornir_shared.misc` per the [Unified-Logging-Convention](../../rules/Unified-Logging-Convention.mdc); never write parity reports or debug dumps to ad hoc files.
- Volumes can be large: stream and bound memory per [Streaming-and-memory-bounded-processing](../../rules/Streaming-and-memory-bounded-processing.mdc); never load a whole SQLite tree into one list when iterating per container will do.
- Test volumes: `tests/pipeline/setup_pipeline.py` fixtures and `TESTINPUTPATH` volumes. A stage needing real volumes, with none on this machine, ends the wake with a proposal instead of an edit.
- Every port commit is high risk (SKILL.md Model routing) and gets the reviewer.

## Stages

Record the current stage in ledger `portStage`, and each completed stage's evidence in `portEvidence` (test names and counts, parity result per fixture volume, timings).

0. **Characterize.** Golden tests pinning today's behavior on fixture volumes:
   - save-then-load round trip, sharded and single-file layouts, comparing the full tree;
   - result sets of every distinct `find`/`findall`/`Iterate`/`Select` XPath pattern in `Pipelines.xml` and `operations/` (first inventory the patterns into `.cursor/issue-handoff/metadata-port/xpath-inventory.md`, noting which use features beyond ElementTree XPath);
   - dirty-flag and `*_Link` resolution behavior.
   Done when the inventory exists and the golden tests pass on current code.
1. **Storage seam.** A small interface under container load/save (e.g. `load_container(path)` / `save_container(node)`), XML implementation only, so `XContainerElementWrapper` no longer calls ElementTree file I/O directly. Done when the golden tests pass unchanged and saved bytes are identical on every fixture volume (file hashes before and after).
2. **Parity tooling.**
   - Harden the comparison in `metadata/migrate.py`: attribute order where XML order is observable, text exactly (report whitespace-only differences separately, not ignored), `*_Link` resolution, child order. Return structured differences, not only logs.
   - Add a Hypothesis `RuleBasedStateMachine` applying the same random sequence of add child, set attribute, remove child, save, and reload to the XML and SQLite backends, asserting equal trees after every step ([hypothesis-testing](../hypothesis-testing/SKILL.md)). Build valid node trees directly; do not filter.
   Done when the machine passes and a deliberately broken backend makes it fail (record the mutation).
3. **Shadow write (opt-in).** A flag (default off) makes each successful XML container save also upsert that container into SQLite and run a cheap parity check on it. A mismatch or SQLite error logs a warning with the container path and never fails the XML save or slows it beyond the measured, recorded cost. Done when the A-class buildmanager and pipeline tests pass with the flag on and off, and shadow-written databases pass the full parity check on every fixture volume.
4. **Safety.** Required before any read path:
   - choose the journal mode per filesystem, detecting and logging the choice: WAL only on local disks; rollback journal (`DELETE`) on network shares, where WAL's shared-memory file is unsafe. Non-local: any `cifs`, `nfs`, `smb3`, `9p`, `drvfs`, `virtiofs`, or `fuse` mount, and any path under `\\` (UNC). In the dev container the bind-mounted `/workspace` and `/nornir-testdata` come from the Windows host through such a filesystem, so a volume there is not a local disk though it looks like one. Test the detection with a mocked mount table;
   - add a cross-process write lock around SQLite writes (SQLite's own lock with a sensible `busy_timeout`, plus a lock for the multi-statement save); whether it should also guard XML is a stage-6 decision;
   - replace delete-all-rows `save` with per-container upserts of only the dirty nodes in one transaction, so a crash leaves the previous state;
   - test concurrent writers (several processes saving different and the same containers) and a network-share volume. With no network share on this machine, make the test skippable, taking a path from an environment variable, and write a proposal asking the user to run it. In the dev container, NAS shares exist only when started with the net-mounts override (`NORNIR_NET_MOUNTS=1`, see `nornir-docker/mount-network-shares.sh`); check `NORNIR_NET_MOUNTS` and use a mounted share if present (in a scratch folder the wake creates and deletes, per gates.md). Never read, copy, or print the credential files.
   Done when concurrency tests pass and the network-share test has passed at least once on a real share (a user-run result recorded in `portEvidence`).
5. **Read path (opt-in).** Behind a second flag (default off), load the wrapper tree from SQLite for a volume whose database passes parity, so existing XPath calls work unchanged. Fall back to XML, with a warning, when the database is missing, has an older schema (run the schema migration), or fails a quick parity check. Do **not** push XPath queries down into SQL here; record candidate pushdowns as proposals with measured load times. Do not start until stage 4's network-share evidence exists. Done when the A-class and pipeline tests pass with reads switched, and load and save timings on a real volume are recorded against XML.
6. **Decisions only.** The loop does not implement these; it writes each as a decision with options and evidence from earlier stages, then waits:
   - make SQLite reads the default, and for which volumes;
   - stop writing XML, or keep it as an export;
   - what to do with the separate XML readers in `nornir-volumemodel` and `nornir-web`, and the external `nornir_djangomodel` importer;
   - typed tables (Block, Section, Channel, Filter, ...) instead of the generic node tree, and whether to normalize attributes;
   - whether a query layer should replace pipeline XPath.

## Port gates

Beyond the general gates, a port wake's change is accepted only if:

- the parity checker passes on every fixture volume the wake can reach;
- the A-class buildmanager and pipeline tests pass with the new flag on and off;
- saved XML bytes are unchanged with the flags off (hash comparison, recorded);
- the network-share and concurrency tests have passed before stage 5 starts;
- the cost of added work (extra save time per container, database size relative to the XML) is measured and recorded, not described as free;
- evidence is recorded in `portEvidence`.

If a stage is larger than one wake, commit the largest slice satisfying these gates, add the remainder to `deferred` with a one-line plan, and keep `portStage` unchanged.
