# Metadata port stage 0: XPath inventory

Inventory of every distinct XPath shape the build pipeline runs against the
volume metadata tree, captured for the XML-to-SQLite metadata port
(`.cursor/skills/nornir-improve-loop/metadata-port.md`, stage 0). Golden tests that
pin the result sets live in
`nornir-buildmanager/tests/test_volume_metadata_characterize.py`; the case table
(`XPATH_CASES`) and fixture builder are in
`nornir-buildmanager/tests/metadata_port_characterize_data.py`.

Captured 2026-10-07 against `nornir-buildmanager` `dev` @ `8fc56b3`; coverage
completed against `7219cb8`. Re-run the commands at the bottom before relying on
the counts.

## Coverage of this inventory

Every distinct pattern below has at least one golden case, with `#Variable` and
`%s`/`{...}` placeholders written as `#v`. No pattern is excluded.
`test_every_inventoried_pattern_has_a_golden_case` re-derives the pattern set from
`Pipelines.xml` (XPath, RowXPath, ColumnXPaths) and from the `find`/`findall`/`iterfind`
arguments in `operations/` and `volumemanager/`, adds the run-time-built patterns
listed in `INDIRECT_PATTERNS`, and fails when the set and the case table disagree in
either direction. A new pattern therefore needs a case (or an entry here and in the
test explaining why it cannot be exercised). The source scan parses each file with
`ast`, so calls split across lines and arguments built from string literals by `+`,
`%`, or f-strings are seen; only an argument that is a bare variable (a template held
in a name) needs an `INDIRECT_PATTERNS` entry.

Matching on pattern text alone cannot tell where a pattern runs. Reporting columns are
evaluated below each `RowXPath` match, so
`test_report_columns_are_pinned_under_their_row_context` also requires, for every
`ColumnXPaths` entry, a case rooted at its row context: the pipeline's
`ReportingElement` Select joined to `RowXPath`, compared with predicates dropped
(`Block/Section` for ImageReport, `Block/StosGroup/SectionMappings` for StosReport).
`Histogram/Image` is a column under both a Filter (through `Channel/Filter[...]/...`)
and a SectionMappings row, and each has its own case.

The XPath cases run on a second fixture, `build_volume(..., extras=True)`, that adds
the nodes only some queries reach: `Scale` on each channel, channel-level `Image`
and `Data`, a `Translated_Prune` transform, `Data` under each filter and prune node,
`AutoLevelHint` and an `InputTransformChecksum` of `hist-<filter>` on each filter
histogram, `NonStosSectionNumbers` on the block, a SectionMappings `Image` with
`InputTransformChecksum`, and a SectionMappings warp `Histogram` (with `Data` and
`Image`) created by the production `GetOrCreateHistogramNodeHelper`, as
`operations/block.py` does for stos warp histograms. The golden-bytes fixture is
unchanged, so `GOLDEN_SHA` did not move. Each case checks `findall` and, on a
separate fresh load, `find`, against plain ElementTree on the link-merged tree.

## How queries reach the tree

- Every query goes through `XElementWrapper.find` / `findall`, which override
  ElementTree's. Only the **first** `/`-separated step is link-aware: it is rewritten
  to `<Tag>_Link<predicates>` (`__ElementLinkNameFromXPath`), matching stubs are
  loaded and swapped in place (`_replace_links`, threaded for more than one), then the
  unlinked step is run with ElementTree and the remainder of the path recurses into
  each match. Deeper links therefore resolve one level at a time.
- A first-step predicate is evaluated against the **stub's** attributes. Stubs copy
  every attribute of the linked child at the parent's last save
  (`_save_link_element`), so they match as long as the parent was re-saved after the
  child changed; `_Save` does rewrite the parent when a linked child has
  `AttributesChanged`.
- `PipelineManager` substitutes `#Variable` tokens (`SubstituteStringVariables`)
  **before** the XPath is evaluated; values are pasted inside `'...'` with no escaping.
- `Iterate` goes through `resolve_iterate_candidates`
  (`pipelinemanager_iterate_filters.py`). With no `Require*` filters (or
  `use_legacy_iterate_fetch()`), it is plain `findall`. With section or transform
  membership filters it may do point lookups instead: `Section[@Number='n']`,
  `Transform[@<attr>='v']`.
- `Select` is `find` (first match), then validation of non-container results.
- `FindParent(tag)` / `FindFromParent(xpath)` walk the in-memory `Parent` chain and
  are not tree queries against stored data.

## Pipelines.xml (`nornir_buildmanager/config/Pipelines.xml`)

135 `Iterate` and 55 `Select` nodes; 33 of them set `Root=` to a variable bound by an
outer node, so the XPath is relative to that node. Counts are occurrences.

| Shape | Iterate | Select | Typical root |
|-------|--------:|-------:|--------------|
| `Block` | 19 | 9 | Volume |
| `Block/Section` | 26 | | Volume |
| `Block/Section/Channel` | 1 | | Volume |
| `Block/Section/Channel/Filter[@Name='#v']` | 3 | | Volume |
| `Block/StosGroup/SectionMappings/Transform` | 2 | | Volume |
| `Block/StosGroup[@Name='StosBrute64']/SectionMappings` | 1 | | Volume |
| `Block/StosGroup[@Name='#v']` | | 1 | Volume |
| `Block/StosMap[@Name='#v']` | 1 | | Volume |
| `Channel` | 26 | | Section |
| `Filter` | 18 | | Channel |
| `Filter[@Name='#v']` | | 5 | Channel |
| `Filter[@Name='#v']/TilePyramid` | | 1 | Channel |
| `TilePyramid` | 2 | 1 | Filter |
| `Tileset` | | 2 | Filter |
| `ImageSet` | | 2 | Filter |
| `ImageSet/Level`, `ImageSet/Level/Image` | 1, 1 | | Filter |
| `Histogram` | 1 | 1 | Filter |
| `Prune`, `Prune[@Overlap='#v']` | | 2, 1 | Filter |
| `Image`, `Data` | 1, 2 | | Channel and Filter (Cleanup); cases also cover Histogram, Prune, Level, SectionMappings |
| `Transform` | 5 | | Channel, SectionMappings |
| `Transform[@Name='#v']` (incl. `Translated_#v`) | | 11 | Channel |
| `TransformData` | 1 | | Channel |
| `StosGroup[@Name='#v#v']`, `StosGroup[@Name='#v']` | 3 | 9 | Block |
| `StosMap[@Name='#v']` | 1 | 8 | Block |
| `SectionMappings/Transform`, `SectionMappings/Transform[@Type='#v']` | 1, 1 | | StosGroup |
| `Mapping` | 3 | | StosMap |

Reporting `PythonCall` arguments (`reporting.GenerateTableReport`):

- ImageReport: `ReportingElement` = `Block`, `RowXPath` `Section`; `ColumnXPaths`
  `Channel/Filter[@Name='#v']`, `Channel/TransformData`, `Channel/Notes`,
  `Channel/Data`, `Channel/Filter[@Name='#v']/Histogram/Image`,
  `Channel/Filter[@Name='#v']/Prune/Image`, each run below a Section.
- StosReport: `ReportingElement` = `Block/StosGroup[@Name='#v']`, `RowXPath`
  `SectionMappings`; `ColumnXPaths` `Image`, `Transform`, `Histogram/Image`, each run
  below a SectionMappings (the warp histogram's image).

## operations/ and volumemanager/ call sites

Literal or formatted XPaths passed to `find`/`findall` (excluding `str.find`):

- Tags only: `Block`, `Section`, `Channel`, `Filter`, `TilePyramid`, `Tileset`,
  `ImageSet`, `Histogram`, `Image`, `Data`, `Scale`, `Notes`, `Mapping`, `Transform`,
  `Level`, `StosGroup`, `StosMap`, `SectionMappings`, `AutoLevelHint`,
  `NonStosSectionNumbers`.
- Paths: `Section/Channel`, `Block/Section/Channel/Scale`, `Filter/TilePyramid/Level`
  (diagnostics.py).
- Predicates, formatted at run time:
  - `Section[@Number='%d']` (vikingxml.py, protected export; read only);
  - `Filter/TilePyramid/Level[@Downsample='%s']` (diagnostics.py);
  - `Image[@InputTransformChecksum='%s']` (block.py);
  - `Histogram[@InputTransformChecksum='<checksum>']` (tile.py
    `_ClearInvalidHistogramElements`, run on a Filter): built at run time by string
    concatenation (`"...='" + checksum + "']"`) on a continuation line, which the
    earlier line-regex scan missed; the checksum is pasted unescaped;
  - `SectionMappings[@MappedSectionNumber='%d']/Transform[@ControlSectionNumber='%d']`
    (block.py template, call site commented out);
  - `Mapping[@Control='%s']`, `StosGroup[@Name='%s']`, `*[@Path='%s']` (volumemanager);
  - `Transform[@ControlSectionNumber='%s']`, `Transform[@MappedSectionNumber='%s']`
    (iterate point lookups, `pipelinemanager_iterate_filters.py`);
  - `Block[@Name='%s']`, `Channel[@Name='%s']`, `Filter[@Name='%s']` (iterate literal
    lookups through `GetChildByAttrib`);
  - `GetChildByAttrib` / `GetChildrenByAttrib` build `Tag[@Attr='%g']` for floats
    (so `1.0` finds `Downsample="1"`) or `Tag[@Attr='%s']` otherwise; pinned in
    `test_get_child_by_attrib_formats_floats_with_g`, with `Level[@Downsample='#v']`
    as the table case;
  - `UpdateOrAddChildByAttrib` builds `Tag[@A='v']` for one name (default `Name`) and
    `Tag[@A='v' and @B='w']` for several. ElementTree rejects `and` with
    `SyntaxError: invalid predicate`; the only multi-name caller
    (`stosgroupnode.py`) is commented out. Pinned as rejected in
    `test_multi_attribute_update_or_add_is_rejected` rather than given a table case.
- Reporting `RecursiveReportGenerator` runs caller-supplied XPaths with `findall`.

## ElementTree limitations that shape the port

None of the inventoried patterns use XPath beyond ElementTree's subset:
`test_pipeline_xpaths_use_only_simple_steps` asserts every `Pipelines.xml` XPath is
`Tag` or `Tag[@Attr='value']` steps joined by `/`. Consequences:

- **No `and` / `or`.** Multi-criteria lookups are hand-written loops
  (`SectionMappingsNode.FindStosTransform` says so); `Require*` nodes filter
  candidates in Python after the fetch.
- **No `*_Link` wildcard.** A wildcard first step (`*[@Path='%s']`, used by
  `XContainerElementWrapper` to detect unlinked subdirectories) loads every matching
  child and filters link tags in Python. `findall` also re-resolves any `*_Link` left
  among its matches, so its pre-load and that fallback mask each other: mutating
  either alone leaves results unchanged (recorded as equivalent in the mutation run).
- **String-only predicates.** `[@Downsample='1']` does not match `1.0`; numbers must be
  formatted exactly as saved (`%g` in `GetChildByAttrib`, `%d` in templates).
- **No escaping.** A substituted value containing `'` produces an invalid XPath. A
  value containing `/` is split by `__ElementLinkNameFromXPath` before ElementTree
  sees it.
- **Lazy resolution is part of the contract.** `find("Block/Section[@Number='2']")`
  loads only the matching section's file; a SQLite read path that materializes the
  whole tree changes memory and timing even if results match
  (`test_links_resolve_lazily_and_only_where_matched`).
- **Document order is observable.** `find` returns the first match and `Iterate`
  walks results in child order, so a backend must preserve child order. Today an
  attribute-only container save writes children in reverse of their loaded order
  (`test_attribute_only_save_reverses_child_order`): `sort()` sorts descending and
  `_Save` walks `list(self)[::-1]`, but the sort only runs when `ChildrenChanged`.
  On-disk order therefore flips on each such save. Even a sorting save only groups
  by tag (`SortKey` is the tag and the sort is stable), so same-tag siblings such as
  `Filter` or `Transform` are written in reverse of their in-memory order on every
  save (`test_parent_sort_leaves_attribute_only_children_unsorted`). Pinned, not
  fixed, because a fix changes saved bytes (decision `port-child-order-flip` in the
  loop ledger).

## Reproduce

`pytest nornir-buildmanager/tests/test_volume_metadata_characterize.py -k "inventoried or row_context"`
checks the case table against the current sources. The raw counts come from the
commands below; the `rg` line is a quick look only and misses concatenated or
multi-line arguments (the test's `ast` scan is authoritative):

```bash
cd nornir-buildmanager/nornir_buildmanager
python - <<'EOF'
from xml.etree import ElementTree as ET
from collections import Counter
c = Counter((e.tag, e.attrib['XPath']) for e in ET.parse('config/Pipelines.xml').iter() if 'XPath' in e.attrib)
for (tag, xp), n in sorted(c.items()): print(n, tag, xp)
EOF
rg -o --no-filename "\.(find|findall|iterfind)\((f?['\"][^'\"]*['\"])" -r '$1 $2' operations/ volumemanager/ | sort | uniq -c
```
